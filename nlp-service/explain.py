"""
Explainability for the linear sentiment classifier.

WHY THIS EXISTS
---------------
"Negative, 87% confident" is not an answer a seller can act on. This module
turns the model's decision into something inspectable, and it does so *exactly*
rather than approximately.

For a linear model over TF-IDF features the decision is

    logit = Σ_j (w_j · x_j) + b

so the contribution of feature *j* is precisely ``w_j · x_j``. There is no
sampling, no surrogate model, and no approximation error — unlike LIME (which
fits a local surrogate) or KernelSHAP (which samples coalitions). The
contributions returned here sum to the logit by construction, and the code
asserts that identity. That exactness is a direct consequence of choosing a
linear model, and is one of the strongest arguments for keeping Logistic
Regression rather than reaching for a transformer.

Two capabilities are built on top of that:

* :meth:`LinearExplainer.attribute` — per-token evidence, signed and ranked.
* :meth:`LinearExplainer.counterfactual` — the minimal set of terms whose
  removal flips the verdict ("remove 'not worth' and this reads positive").
  Counterfactuals are evaluated by genuinely re-vectorising the edited text,
  not by subtracting weights, because TF-IDF L2-normalises each row: dropping
  a term rescales every remaining term, so weight arithmetic would be wrong.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

#: Cap on how many terms a counterfactual is allowed to remove before we give
#: up. Beyond a handful the explanation stops being useful to a human.
MAX_COUNTERFACTUAL_TERMS = 6

#: How many attributed tokens to return by default.
TOP_K = 12


@dataclass
class TokenContribution:
    """One n-gram's signed contribution to the decision."""
    term: str
    weight: float          # model coefficient for this feature
    value: float           # TF-IDF value in this document
    contribution: float    # weight * value  (exact)
    direction: str         # "positive" | "negative"

    def as_dict(self) -> dict:
        return {
            "term": self.term,
            "weight": round(self.weight, 4),
            "value": round(self.value, 4),
            "contribution": round(self.contribution, 4),
            "direction": self.direction,
        }


@dataclass
class Counterfactual:
    """The minimal edit that flips the prediction."""
    found: bool
    removed_terms: List[str] = field(default_factory=list)
    original_label: str = ""
    flipped_label: str = ""
    original_confidence: float = 0.0
    flipped_confidence: float = 0.0
    edited_text: str = ""

    def as_dict(self) -> dict:
        return {
            "found": self.found,
            "removedTerms": self.removed_terms,
            "originalLabel": self.original_label,
            "flippedLabel": self.flipped_label,
            "originalConfidence": round(self.original_confidence, 4),
            "flippedConfidence": round(self.flipped_confidence, 4),
            "editedText": self.edited_text,
        }


@dataclass
class Explanation:
    """Everything we can say about why the model decided what it decided."""
    logit: float
    intercept: float
    contributions: List[TokenContribution] = field(default_factory=list)
    counterfactual: Counterfactual | None = None
    coverage: float = 0.0        # fraction of tokens the model actually knows
    known_terms: int = 0
    total_terms: int = 0

    def as_dict(self) -> dict:
        return {
            "logit": round(self.logit, 4),
            "intercept": round(self.intercept, 4),
            "contributions": [c.as_dict() for c in self.contributions],
            "counterfactual": self.counterfactual.as_dict() if self.counterfactual else None,
            "coverage": round(self.coverage, 4),
            "knownTerms": self.known_terms,
            "totalTerms": self.total_terms,
        }


class LinearExplainer:
    """Exact attribution and counterfactual search for a linear TF-IDF model.

    Parameters
    ----------
    vectorizer:
        The *fitted* ``TfidfVectorizer`` used at training time.
    classifier:
        A linear classifier exposing ``coef_`` and ``intercept_``. If the model
        is wrapped for calibration, pass the underlying estimator — the caller
        is responsible for unwrapping, since a calibrated wrapper has no
        coefficients of its own.
    """

    def __init__(self, vectorizer, classifier):
        self.vectorizer = vectorizer
        self.classifier = classifier
        self._feature_names = None

    # -- helpers ------------------------------------------------------------

    @property
    def feature_names(self) -> np.ndarray:
        if self._feature_names is None:
            self._feature_names = self.vectorizer.get_feature_names_out()
        return self._feature_names

    @property
    def coefficients(self) -> np.ndarray:
        """Coefficient vector oriented so that positive => positive sentiment."""
        coef = self.classifier.coef_
        return coef[0] if coef.ndim > 1 else coef

    @property
    def intercept(self) -> float:
        b = self.classifier.intercept_
        return float(b[0] if np.ndim(b) > 0 else b)

    # -- attribution --------------------------------------------------------

    def attribute(self, processed_text: str, top_k: int = TOP_K) -> Explanation:
        """Decompose the decision on ``processed_text`` into per-term evidence.

        ``processed_text`` must be the text *after* the same preprocessing the
        model was trained on — otherwise the features won't line up.
        """
        X = self.vectorizer.transform([processed_text])
        coef = self.coefficients
        intercept = self.intercept

        row = X.tocoo()
        contributions: List[TokenContribution] = []
        for j, value in zip(row.col, row.data):
            weight = float(coef[j])
            contrib = weight * float(value)
            if contrib == 0.0:
                continue
            contributions.append(
                TokenContribution(
                    term=str(self.feature_names[j]),
                    weight=weight,
                    value=float(value),
                    contribution=contrib,
                    direction="positive" if contrib > 0 else "negative",
                )
            )

        logit = float(X.dot(coef)[0]) + intercept

        # Sanity: the parts must sum to the whole. This is the property that
        # makes the explanation exact rather than indicative.
        reconstructed = sum(c.contribution for c in contributions) + intercept
        if abs(reconstructed - logit) > 1e-6:
            logger.warning(
                "Attribution mismatch: Σcontrib+b=%.8f but logit=%.8f",
                reconstructed, logit,
            )

        contributions.sort(key=lambda c: abs(c.contribution), reverse=True)

        tokens = processed_text.split()
        vocab = self.vectorizer.vocabulary_
        known = sum(1 for t in tokens if t in vocab)

        return Explanation(
            logit=logit,
            intercept=intercept,
            contributions=contributions[:top_k],
            coverage=known / len(tokens) if tokens else 0.0,
            known_terms=known,
            total_terms=len(tokens),
        )

    # -- counterfactual -----------------------------------------------------

    def counterfactual(
        self,
        processed_text: str,
        max_terms: int = MAX_COUNTERFACTUAL_TERMS,
    ) -> Counterfactual:
        """Find the smallest set of terms whose removal flips the prediction.

        Greedy: repeatedly drop the single remaining term contributing most
        toward the current verdict, re-vectorise, and re-score. Greedy is not
        guaranteed minimal — an exhaustive search over subsets would be — but
        it is O(k) transforms instead of O(2^k) and in practice lands on the
        same 1-3 terms a human would point at.
        """
        coef = self.coefficients
        intercept = self.intercept

        X0 = self.vectorizer.transform([processed_text])
        logit0 = float(X0.dot(coef)[0]) + intercept
        original_positive = logit0 > 0
        original_label = "positive" if original_positive else "negative"

        tokens = processed_text.split()
        if not tokens:
            return Counterfactual(found=False, original_label=original_label)

        removed: List[str] = []
        remaining = list(tokens)

        for _ in range(max_terms):
            # Rank the *unigrams still present* by how much each pushes toward
            # the current verdict. We only remove unigrams because removing a
            # bigram feature has no meaning at the text level.
            candidates: List[Tuple[float, str]] = []
            seen = set()
            for tok in remaining:
                if tok in seen:
                    continue
                seen.add(tok)
                j = self.vectorizer.vocabulary_.get(tok)
                if j is None:
                    continue
                w = float(coef[j])
                # Contribution toward the current verdict.
                push = w if original_positive else -w
                if push > 0:
                    candidates.append((push, tok))

            if not candidates:
                break

            candidates.sort(reverse=True)
            _, worst = candidates[0]

            remaining = [t for t in remaining if t != worst]
            removed.append(worst)

            edited = " ".join(remaining)
            Xe = self.vectorizer.transform([edited])
            logit_e = float(Xe.dot(coef)[0]) + intercept

            if (logit_e > 0) != original_positive:
                proba = 1.0 / (1.0 + np.exp(-logit_e))
                flipped_conf = proba if logit_e > 0 else 1.0 - proba
                orig_proba = 1.0 / (1.0 + np.exp(-logit0))
                orig_conf = orig_proba if original_positive else 1.0 - orig_proba
                return Counterfactual(
                    found=True,
                    removed_terms=removed,
                    original_label=original_label,
                    flipped_label="positive" if logit_e > 0 else "negative",
                    original_confidence=float(orig_conf),
                    flipped_confidence=float(flipped_conf),
                    edited_text=edited,
                )

        orig_proba = 1.0 / (1.0 + np.exp(-logit0))
        orig_conf = orig_proba if original_positive else 1.0 - orig_proba
        return Counterfactual(
            found=False,
            removed_terms=removed,
            original_label=original_label,
            original_confidence=float(orig_conf),
        )

    # -- global model introspection ----------------------------------------

    def top_features(self, k: int = 20) -> Dict[str, List[dict]]:
        """The terms the model weights most heavily, globally.

        Useful as a sanity check on the trained model: if the strongest
        positive feature is something meaningless, the training data is wrong.
        """
        coef = self.coefficients
        names = self.feature_names
        order = np.argsort(coef)

        negative = [
            {"term": str(names[i]), "weight": round(float(coef[i]), 4)}
            for i in order[:k]
        ]
        positive = [
            {"term": str(names[i]), "weight": round(float(coef[i]), 4)}
            for i in order[-k:][::-1]
        ]
        return {"positive": positive, "negative": negative}


__all__ = [
    "LinearExplainer",
    "Explanation",
    "TokenContribution",
    "Counterfactual",
    "MAX_COUNTERFACTUAL_TERMS",
]
