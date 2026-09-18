"""
Sentiment engine for Amazon review classification.

DESIGN
------
The classifier is a **hybrid** of two independent signals:

1. **Learned** — TF-IDF (unigrams + bigrams) into a calibrated Logistic
   Regression. Strong on vocabulary it has seen; useless on vocabulary it
   hasn't.

2. **Rule-based** — the valence lexicon in :mod:`lexicon`, with negation
   scope, intensifiers and contrastive handling. Weaker on nuance, but it
   never has an out-of-vocabulary problem and it gets negation right by
   construction.

They are combined with a confidence-weighted blend, and — critically — the
blend weight *shifts toward the lexicon as model coverage drops*. This fixes
the original pipeline's most dangerous failure: a review made of unseen words
produced an all-zero TF-IDF row, so the prediction collapsed to the intercept
and the service returned a confident-looking verdict derived from no evidence
whatsoever. Now that case is detected (``coverage``) and handled.

Beyond the binary verdict the engine reports:

* ``mixed`` as a first-class outcome, when the aspect-level opinions genuinely
  disagree — real reviews are frequently "great X, terrible Y", and forcing
  that into positive/negative discards the most useful information in them
* calibrated confidence (``CalibratedClassifierCV``), so 0.8 means something
  closer to "right 80% of the time" than an arbitrary sigmoid output
* honest evaluation: precision/recall/F1 per class, a confusion matrix and
  cross-validated scores rather than a single accuracy number on data the
  model has effectively memorised
"""

from __future__ import annotations

import logging
import os
import pickle
import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import matplotlib
import nltk
import numpy as np
import spacy
from imblearn.over_sampling import SMOTE
from nltk.corpus import stopwords
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.manifold import TSNE
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

matplotlib.use("Agg")  # headless: no display inside the container
import matplotlib.pyplot as plt  # noqa: E402

from aspects import AspectAnalysis, AspectExtractor  # noqa: E402
from corpus import load_training_data  # noqa: E402
from explain import LinearExplainer  # noqa: E402
from lexicon import LexiconSentiment  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "classifier.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")
SMOTE_DIST_PATH = os.path.join(MODEL_DIR, "smote_distribution.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.pkl")
MANIFEST_PATH = os.path.join(MODEL_DIR, "manifest.pkl")

#: Bumped whenever the pipeline changes in a way that invalidates a cached
#: model. Without this, a stale pickle from an older code version loads
#: silently and serves predictions from a pipeline that no longer exists.
MODEL_VERSION = "2.0.0"

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "nothing", "nobody", "nowhere",
    "none", "cannot", "can't", "won't", "didn't", "doesn't", "isn't",
    "wasn't", "aren't", "wouldn't", "couldn't", "shouldn't", "don't",
    "hasn't", "haven't", "hardly", "barely", "rarely", "without",
}

#: Below this share of known tokens the learned model is not trusted on its own.
LOW_COVERAGE_THRESHOLD = 0.34

#: Below this the review is reported as low-confidence rather than a verdict.
UNCERTAIN_BAND = 0.58

#: Fallback lexicon weight, used only before the first training run measures
#: the real one. Bounded so a degenerate measurement can never let one engine
#: silence the other entirely.
DEFAULT_BLEND_WEIGHT = 2.0
MIN_BLEND_WEIGHT = 0.5
MAX_BLEND_WEIGHT = 5.0

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SentimentResult:
    """One review's full analysis."""
    label: str                    # positive | negative | mixed
    confidence: float
    processed_text: str
    model_label: str = ""         # what the learned classifier alone said
    model_confidence: float = 0.0
    lexicon_label: str = ""       # what the rule engine alone said
    lexicon_score: float = 0.0
    coverage: float = 0.0         # share of tokens the model recognises
    low_signal: bool = False      # model had (almost) nothing to work with
    uncertain: bool = False       # blended confidence inside the grey band
    agreement: bool = True        # did the two engines agree?
    conflict_score: float = 0.0   # aspect-level disagreement, 0..1

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "processedText": self.processed_text,
            "modelLabel": self.model_label,
            "modelConfidence": round(self.model_confidence, 4),
            "lexiconLabel": self.lexicon_label,
            "lexiconScore": round(self.lexicon_score, 4),
            "coverage": round(self.coverage, 4),
            "lowSignal": self.low_signal,
            "uncertain": self.uncertain,
            "agreement": self.agreement,
            "conflictScore": round(self.conflict_score, 4),
        }


# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

class TextPreprocessor:
    """Cleaning, stopword removal and lemmatisation for the learned model.

    Only the *classifier* consumes this output. The aspect layer deliberately
    works on raw text, because dependency parsing needs real grammar —
    determiners, verbs and word order — which this pipeline strips away.
    """

    def __init__(self):
        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:  # pragma: no cover - depends on image build
            nltk.download("stopwords", quiet=True)

        # Negation words are deliberately retained. NLTK's English stopword
        # list contains "not"; removing it turns "not good" into "good" and
        # silently inverts the label. Keeping them only pays off because the
        # vectoriser below uses ngram_range=(1, 2), so "not good" survives as
        # a single feature distinct from "good".
        self.stop_words = set(stopwords.words("english")) - NEGATION_WORDS
        self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"http\S+|www\.\S+", " ", text)
        # Apostrophes are kept so contractions survive as negators
        # ("isn't" -> "isn't", not "isn" + "t").
        text = re.sub(r"[^a-zA-Z'\s]", " ", text)
        text = text.lower().strip()
        return re.sub(r"\s+", " ", text)

    def remove_stopwords(self, text: str) -> str:
        return " ".join(w for w in text.split() if w not in self.stop_words)

    def lemmatize_text(self, text: str) -> str:
        doc = self.nlp(text)
        return " ".join(token.lemma_ for token in doc)

    def preprocess(self, text: str) -> str:
        return self.lemmatize_text(self.remove_stopwords(self.clean_text(text)))

    def preprocess_batch(self, texts: Sequence[str], batch_size: int = 500) -> List[str]:
        """Batch preprocessing — one ``nlp.pipe`` call instead of N."""
        cleaned = [self.remove_stopwords(self.clean_text(t)) for t in texts]
        return [
            " ".join(tok.lemma_ for tok in doc)
            for doc in self.nlp.pipe(cleaned, batch_size=batch_size)
        ]


# ---------------------------------------------------------------------------
# Aspect analyser (thin wrapper keeping the original public shape)
# ---------------------------------------------------------------------------

class NLPAnalyzer:
    """POS tagging + dependency parsing + aspect polarity."""

    def __init__(self, lexicon: LexiconSentiment | None = None):
        # Full pipeline here — the parser is required, because the aspect
        # extractor reads token.dep_ and token.head.
        self.nlp = spacy.load("en_core_web_sm")
        self.extractor = AspectExtractor(lexicon or LexiconSentiment())

    def analyze(self, text: str) -> AspectAnalysis:
        return self.extractor.analyze(self.nlp(text))

    def analyze_batch(self, texts: Sequence[str], batch_size: int = 500) -> List[AspectAnalysis]:
        return [
            self.extractor.analyze(doc)
            for doc in self.nlp.pipe(texts, batch_size=batch_size)
        ]


# ---------------------------------------------------------------------------
# Sentiment model
# ---------------------------------------------------------------------------

class SentimentModel:
    """Hybrid learned + rule-based sentiment engine."""

    def __init__(self, preprocessor: TextPreprocessor):
        self.preprocessor = preprocessor
        self.lexicon = LexiconSentiment()
        self.vectorizer: TfidfVectorizer | None = None
        self.classifier = None                    # calibrated wrapper
        self.base_classifier: LogisticRegression | None = None  # for coefficients
        self.smote_distribution: dict = {}
        self.metrics: dict = {}
        self.manifest: dict = {}
        #: Relative weight of the lexicon in the blend. Overwritten at training
        #: time by the measured odds ratio; this default applies only before a
        #: model has been trained.
        self.blend_weight: float = DEFAULT_BLEND_WEIGHT
        self._explainer: LinearExplainer | None = None

    # -- explainer ----------------------------------------------------------

    @property
    def explainer(self) -> LinearExplainer | None:
        """Lazily built explainer over the *uncalibrated* linear model.

        A ``CalibratedClassifierCV`` has no ``coef_`` of its own — it wraps the
        estimator — so attribution must run against the base model.
        """
        if self._explainer is None and self.vectorizer is not None and self.base_classifier is not None:
            self._explainer = LinearExplainer(self.vectorizer, self.base_classifier)
        return self._explainer

    # -- persistence --------------------------------------------------------

    def save(self):
        with open(CLASSIFIER_PATH, "wb") as f:
            pickle.dump({"calibrated": self.classifier, "base": self.base_classifier}, f)
        with open(VECTORIZER_PATH, "wb") as f:
            pickle.dump(self.vectorizer, f)
        with open(SMOTE_DIST_PATH, "wb") as f:
            pickle.dump(self.smote_distribution, f)
        with open(METRICS_PATH, "wb") as f:
            pickle.dump(self.metrics, f)
        with open(MANIFEST_PATH, "wb") as f:
            pickle.dump(self.manifest, f)
        logger.info("Model artefacts saved to %s", MODEL_DIR)

    def load(self) -> bool:
        """Load a cached model, rejecting artefacts from an older pipeline."""
        if not (os.path.exists(CLASSIFIER_PATH) and os.path.exists(VECTORIZER_PATH)):
            return False

        # Version gate. Both files must exist AND the manifest must match, or
        # we retrain — a mismatched vectoriser/classifier pair produces
        # silently wrong predictions with no error at all.
        manifest = {}
        if os.path.exists(MANIFEST_PATH):
            try:
                with open(MANIFEST_PATH, "rb") as f:
                    manifest = pickle.load(f)
            except Exception:
                logger.warning("Manifest unreadable — retraining")
                return False

        if manifest.get("modelVersion") != MODEL_VERSION:
            logger.info(
                "Cached model is version %s but this build expects %s — retraining",
                manifest.get("modelVersion"), MODEL_VERSION,
            )
            return False

        try:
            with open(CLASSIFIER_PATH, "rb") as f:
                blob = pickle.load(f)
            with open(VECTORIZER_PATH, "rb") as f:
                self.vectorizer = pickle.load(f)
        except Exception:
            logger.exception("Failed to unpickle model — retraining")
            return False

        self.classifier = blob.get("calibrated")
        self.base_classifier = blob.get("base")
        self.manifest = manifest

        for path, attr in ((SMOTE_DIST_PATH, "smote_distribution"), (METRICS_PATH, "metrics")):
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        setattr(self, attr, pickle.load(f))
                except Exception:
                    logger.warning("Could not load %s", path)

        # The blend weight was measured at training time; recover it rather
        # than silently falling back to the default.
        self.blend_weight = float(manifest.get("blendWeight", DEFAULT_BLEND_WEIGHT))

        self._explainer = None
        logger.info(
            "Model %s loaded from disk (blend weight %.2f)",
            MODEL_VERSION, self.blend_weight,
        )
        return True

    # -- training -----------------------------------------------------------

    def train(self, size: int | None = None):
        """Full training pipeline with honest evaluation."""
        texts, labels, source = load_training_data(**({"size": size} if size else {}))
        logger.info("Training corpus: %s", source)

        processed = self.preprocessor.preprocess_batch(texts)
        y = np.array(labels)

        self.vectorizer = TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),     # bigrams are what let "not good" be learned
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
        )

        # Fit the vectoriser on the TRAINING SPLIT ONLY. Fitting on everything
        # first leaks test-set vocabulary and IDF statistics into training and
        # inflates every score that follows.
        idx_train, idx_test = train_test_split(
            np.arange(len(processed)), test_size=0.2, random_state=42, stratify=y,
        )
        train_texts = [processed[i] for i in idx_train]
        test_texts = [processed[i] for i in idx_test]
        y_train, y_test = y[idx_train], y[idx_test]

        X_train = self.vectorizer.fit_transform(train_texts)
        X_test = self.vectorizer.transform(test_texts)

        unique, counts = np.unique(y_train, return_counts=True)
        before_dist = {str(u): int(c) for u, c in zip(unique, counts)}
        logger.info("Class distribution BEFORE SMOTE: %s", before_dist)

        self._plot_tsne(X_train, y_train, "tsne_before.png", "t-SNE Before SMOTE")

        # SMOTE on the TRAINING SPLIT ONLY. Resampling before the split would
        # interpolate synthetic points between rows that later land in the test
        # set — textbook data leakage.
        X_resampled, y_resampled = X_train, y_train
        if len(unique) > 1 and counts.min() > 1:
            smote = SMOTE(
                sampling_strategy="auto",
                k_neighbors=min(5, int(counts.min()) - 1),
                random_state=42,
            )
            X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

        unique_a, counts_a = np.unique(y_resampled, return_counts=True)
        after_dist = {str(u): int(c) for u, c in zip(unique_a, counts_a)}
        logger.info("Class distribution AFTER SMOTE:  %s", after_dist)
        self.smote_distribution = {"before": before_dist, "after": after_dist}

        self._plot_tsne(X_resampled, y_resampled, "tsne_after.png", "t-SNE After SMOTE")

        # Base model — kept unwrapped so the explainer can read coefficients.
        self.base_classifier = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs")
        self.base_classifier.fit(X_resampled, y_resampled)

        # Calibrated wrapper for trustworthy probabilities. Raw LR sigmoid
        # output is not a reliable probability once SMOTE has distorted the
        # class prior; isotonic/sigmoid calibration on held-out folds corrects
        # for that so "0.8 confident" means something.
        self.classifier = CalibratedClassifierCV(
            LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs"),
            method="sigmoid",
            cv=3,
        )
        self.classifier.fit(X_resampled, y_resampled)

        self.metrics = self._evaluate(
            X_test, y_test, X_resampled, y_resampled, source, len(texts),
        )

        # Measure both engines on out-of-distribution text and set the blend
        # weight from the result. This has to happen after the classifier is
        # fitted but before the model is used to serve anything.
        self.metrics["outOfDistribution"] = self._measure_blend_weight()
        self.manifest = {
            "modelVersion": MODEL_VERSION,
            "trainedOn": source,
            "samples": len(texts),
            "features": int(len(self.vectorizer.vocabulary_)),
            "blendWeight": self.blend_weight,
        }

        self._explainer = None
        self.save()
        logger.info(
            "Training complete — macro-F1 %.3f, accuracy %.3f",
            self.metrics.get("macroF1", 0.0), self.metrics.get("accuracy", 0.0),
        )

    # -- evaluation ---------------------------------------------------------

    def _evaluate(
        self, X_test, y_test, X_train, y_train, source: str, n_samples: int,
    ) -> dict:
        """Honest metrics.

        Accuracy alone is misleading on imbalanced data — always predicting the
        majority class scores 70% on a 70/30 split while being useless. Macro-F1
        weights both classes equally, and the confusion matrix shows *which*
        mistake the model makes.
        """
        y_pred = self.classifier.predict(X_test)
        y_proba = self.classifier.predict_proba(X_test)[:, 1]

        precision, recall, f1, support = precision_recall_fscore_support(
            y_test, y_pred, labels=[0, 1], zero_division=0,
        )
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        tn, fp, fn, tp = (int(v) for v in cm.ravel()) if cm.size == 4 else (0, 0, 0, 0)

        try:
            auc = float(roc_auc_score(y_test, y_proba))
        except ValueError:
            auc = float("nan")

        # Cross-validation on the resampled training data gives a stability
        # estimate: a large gap between CV mean and the held-out score is a
        # strong signal of overfitting.
        try:
            cv = cross_val_score(
                LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs"),
                X_train, y_train,
                cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                scoring="f1_macro",
            )
            cv_mean, cv_std = float(cv.mean()), float(cv.std())
        except Exception:
            cv_mean, cv_std = float("nan"), float("nan")

        report = classification_report(
            y_test, y_pred, labels=[0, 1],
            target_names=["negative", "positive"],
            zero_division=0, output_dict=True,
        )

        return {
            "modelVersion": MODEL_VERSION,
            "trainedOn": source,
            "trainingSamples": int(n_samples),
            "testSamples": int(len(y_test)),
            "vocabularySize": int(len(self.vectorizer.vocabulary_)),
            "accuracy": float(report["accuracy"]),
            "macroF1": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
            "weightedF1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            "rocAuc": auc,
            "crossValF1Mean": cv_mean,
            "crossValF1Std": cv_std,
            "perClass": {
                "negative": {
                    "precision": float(precision[0]), "recall": float(recall[0]),
                    "f1": float(f1[0]), "support": int(support[0]),
                },
                "positive": {
                    "precision": float(precision[1]), "recall": float(recall[1]),
                    "f1": float(f1[1]), "support": int(support[1]),
                },
            },
            "confusionMatrix": {
                "trueNegative": tn, "falsePositive": fp,
                "falseNegative": fn, "truePositive": tp,
            },
        }

    # -- out-of-distribution calibration of the blend -----------------------

    def _measure_blend_weight(self) -> dict:
        """Score both engines on held-out realistic text and set the blend weight.

        This is the most important number the project produces. The in-
        distribution metrics above are computed on a split of the *same*
        generated corpus the model trained on, so they measure how well the
        model memorised the generator — not how well it reads reviews. The
        benchmark in :mod:`benchmark` is hand-written, deliberately unlike the
        training templates, and full of the constructions that break sentiment
        classifiers: negation, contrastive mixing, implicit sentiment, sarcasm,
        misspellings.

        Each engine is scored *conditionally* — only on the cases where it
        actually participates in the blend — because that is the accuracy the
        weight should reflect. The weight is then their odds ratio, clamped.
        """
        from benchmark import BENCHMARK, score_predictions  # local: optional at runtime

        texts = [t for t, _ in BENCHMARK]
        expected = [l for _, l in BENCHMARK]

        processed = self.preprocessor.preprocess_batch(texts)
        X = self.vectorizer.transform(processed)
        probas = self.classifier.predict_proba(X)[:, 1]

        model_preds, lex_preds = [], []
        model_hits = model_n = lex_hits = lex_n = 0

        for i, (text, exp) in enumerate(zip(texts, expected)):
            coverage, _, _ = self._coverage(processed[i])
            m_label = "positive" if probas[i] >= 0.5 else "negative"
            lex = self.lexicon.score(text)

            model_preds.append(m_label)
            lex_preds.append(lex.label)

            if exp == "neutral":
                continue
            if coverage >= LOW_COVERAGE_THRESHOLD:
                model_n += 1
                model_hits += (m_label == exp)
            if lex.has_signal:
                lex_n += 1
                lex_hits += (lex.label == exp)

        model_acc = model_hits / model_n if model_n else 0.5
        lex_acc = lex_hits / lex_n if lex_n else 0.5

        def odds(a: float) -> float:
            a = min(max(a, 1e-3), 1 - 1e-3)
            return a / (1.0 - a)

        weight = odds(lex_acc) / odds(model_acc) if model_acc > 0 else DEFAULT_BLEND_WEIGHT
        self.blend_weight = float(min(MAX_BLEND_WEIGHT, max(MIN_BLEND_WEIGHT, weight)))

        model_score = score_predictions(expected, model_preds)
        lex_score = score_predictions(expected, lex_preds)

        logger.info(
            "OOD benchmark — model %.1f%%, lexicon %.1f%%, blend weight %.2f",
            100 * model_score["polarAccuracy"],
            100 * lex_score["polarAccuracy"],
            self.blend_weight,
        )

        return {
            "benchmarkSize": len(BENCHMARK),
            "modelAccuracy": round(model_score["polarAccuracy"], 4),
            "lexiconAccuracy": round(lex_score["polarAccuracy"], 4),
            "modelConditionalAccuracy": round(model_acc, 4),
            "lexiconConditionalAccuracy": round(lex_acc, 4),
            "blendWeight": round(self.blend_weight, 4),
            "note": (
                "Hand-written realistic reviews, deliberately unlike the training "
                "corpus. This is the honest generalisation estimate; the "
                "in-distribution accuracy above is not."
            ),
        }

    # -- t-SNE --------------------------------------------------------------

    @staticmethod
    def _plot_tsne(X, y, filename: str, title: str):
        """2-D projection of the TF-IDF space. Diagnostic only — never used
        at prediction time."""
        try:
            n_samples = min(800, X.shape[0])
            idx = np.random.RandomState(42).choice(X.shape[0], n_samples, replace=False)
            X_sub = X[idx]
            y_sub = np.asarray(y)[idx]
            if hasattr(X_sub, "toarray"):
                X_sub = X_sub.toarray()

            tsne = TSNE(
                n_components=2,
                perplexity=max(5, min(30, n_samples - 1)),
                init="pca",
                random_state=42,
            )
            X_2d = tsne.fit_transform(X_sub)

            fig, ax = plt.subplots(figsize=(10, 8))
            colors = {0: "#ef4444", 1: "#22c55e"}
            names = {0: "Negative", 1: "Positive"}
            for cls in (0, 1):
                mask = y_sub == cls
                if not mask.any():
                    continue
                ax.scatter(
                    X_2d[mask, 0], X_2d[mask, 1], c=colors[cls], label=names[cls],
                    alpha=0.6, s=30, edgecolors="w", linewidth=0.5,
                )
            ax.set_title(title, fontsize=14, fontweight="bold")
            ax.legend(fontsize=12)
            ax.set_xlabel("t-SNE 1")
            ax.set_ylabel("t-SNE 2")
            plt.tight_layout()
            fig.savefig(os.path.join(STATIC_DIR, filename), dpi=150)
            plt.close(fig)
            logger.info("t-SNE plot saved -> %s", filename)
        except Exception:
            # A failed diagnostic plot must never break training.
            logger.exception("t-SNE plot %s failed; continuing", filename)

    # -- prediction ---------------------------------------------------------

    def _coverage(self, processed: str) -> Tuple[float, int, int]:
        tokens = processed.split()
        if not tokens or self.vectorizer is None:
            return 0.0, 0, 0
        vocab = self.vectorizer.vocabulary_
        known = sum(1 for t in tokens if t in vocab)
        return known / len(tokens), known, len(tokens)

    def _blend(
        self,
        model_positive_proba: float,
        lexicon_score: float,
        lexicon_has_signal: bool,
        coverage: float,
    ) -> Tuple[str, float, bool]:
        """Combine the two engines into a single verdict.

        The critical distinction — and the bug this replaced — is between an
        engine that says "neutral" and one that says "I don't know". A lexicon
        compound of 0.0 means *no sentiment word was found*, i.e. abstention.
        Treating that as p(positive)=0.5 and averaging it in drags confident,
        correct model predictions toward the middle. Measured on the
        out-of-distribution benchmark, that single confusion cost ~9 points of
        accuracy and made the hybrid worse than the classifier alone.

        So each engine is weighted by how much it actually knows:

        * the model's weight scales with vocabulary **coverage** — how much of
          this review it has ever seen
        * the lexicon's weight scales with the **magnitude** of its compound
          score, and is exactly zero when it found no sentiment-bearing term

        If both abstain there is genuinely nothing to go on, and the caller is
        told so via ``low_signal`` rather than being handed a fabricated verdict.
        """
        # How much does each engine actually know here?
        model_weight = min(1.0, coverage / LOW_COVERAGE_THRESHOLD)
        lexicon_weight = (
            min(1.0, abs(lexicon_score) / 0.25) if lexicon_has_signal else 0.0
        )

        # The lexicon's relative weight is *measured*, not hand-picked: it is
        # the odds ratio of the two engines' conditional accuracy on the
        # out-of-distribution benchmark, computed at training time (see
        # _measure_blend_weight). Train on real data and the model gets better,
        # the ratio drops, and the blend shifts back toward the model
        # automatically. Hard-coding a constant tuned on the eval set would
        # score a couple of points higher on that set and mean nothing.
        lexicon_weight *= self.blend_weight

        total = model_weight + lexicon_weight
        if total <= 1e-9:
            # Neither engine has anything. Report the model's number but flag it.
            return (
                "positive" if model_positive_proba >= 0.5 else "negative",
                0.5,
                True,
            )

        lexicon_positive = (lexicon_score + 1.0) / 2.0
        blended = (
            model_weight * model_positive_proba + lexicon_weight * lexicon_positive
        ) / total

        label = "positive" if blended >= 0.5 else "negative"
        confidence = blended if label == "positive" else 1.0 - blended
        low_signal = coverage < LOW_COVERAGE_THRESHOLD and not lexicon_has_signal
        return label, float(confidence), low_signal

    def predict(self, text: str, analysis: AspectAnalysis | None = None) -> SentimentResult:
        """Classify one review."""
        processed = self.preprocessor.preprocess(text)
        coverage, _, _ = self._coverage(processed)

        X = self.vectorizer.transform([processed])
        model_proba = float(self.classifier.predict_proba(X)[0][1])
        model_label = "positive" if model_proba >= 0.5 else "negative"
        model_conf = model_proba if model_label == "positive" else 1.0 - model_proba

        lex = self.lexicon.score(text)

        label, confidence, low_signal = self._blend(
            model_proba, lex.compound, lex.has_signal, coverage,
        )

        conflict = analysis.conflict_score if analysis else 0.0
        # A genuinely split review is reported as mixed rather than being
        # forced into a binary bucket that discards its most useful content.
        if analysis is not None and analysis.is_mixed:
            label = "mixed"

        return SentimentResult(
            label=label,
            confidence=confidence,
            processed_text=processed,
            model_label=model_label,
            model_confidence=model_conf,
            lexicon_label=lex.label,
            lexicon_score=lex.compound,
            coverage=coverage,
            low_signal=low_signal,
            uncertain=confidence < UNCERTAIN_BAND,
            agreement=(model_label == lex.label) or lex.label == "neutral",
            conflict_score=conflict,
        )

    def predict_batch(
        self,
        texts: Sequence[str],
        analyses: Sequence[AspectAnalysis] | None = None,
        batch_size: int = 500,
    ) -> List[SentimentResult]:
        """Vectorised batch prediction — one spaCy pass, one transform, one
        ``predict_proba`` over the whole matrix."""
        processed = self.preprocessor.preprocess_batch(texts, batch_size=batch_size)
        X = self.vectorizer.transform(processed)
        probas = self.classifier.predict_proba(X)[:, 1]

        results: List[SentimentResult] = []
        for i, text in enumerate(texts):
            coverage, _, _ = self._coverage(processed[i])
            model_proba = float(probas[i])
            model_label = "positive" if model_proba >= 0.5 else "negative"
            model_conf = model_proba if model_label == "positive" else 1.0 - model_proba

            lex = self.lexicon.score(text)
            label, confidence, low_signal = self._blend(
                model_proba, lex.compound, lex.has_signal, coverage,
            )

            analysis = analyses[i] if analyses is not None and i < len(analyses) else None
            conflict = analysis.conflict_score if analysis else 0.0
            if analysis is not None and analysis.is_mixed:
                label = "mixed"

            results.append(
                SentimentResult(
                    label=label,
                    confidence=confidence,
                    processed_text=processed[i],
                    model_label=model_label,
                    model_confidence=model_conf,
                    lexicon_label=lex.label,
                    lexicon_score=lex.compound,
                    coverage=coverage,
                    low_signal=low_signal,
                    uncertain=confidence < UNCERTAIN_BAND,
                    agreement=(model_label == lex.label) or lex.label == "neutral",
                    conflict_score=conflict,
                )
            )
        return results

    # -- explanation --------------------------------------------------------

    def explain(self, text: str, top_k: int = 12) -> dict:
        """Attribution + counterfactual for one review."""
        processed = self.preprocessor.preprocess(text)
        exp = self.explainer
        if exp is None:
            return {}
        explanation = exp.attribute(processed, top_k=top_k)
        explanation.counterfactual = exp.counterfactual(processed)
        payload = explanation.as_dict()
        payload["lexicon"] = self.lexicon.score(text).as_dict()
        return payload

    def top_features(self, k: int = 20) -> dict:
        exp = self.explainer
        return exp.top_features(k) if exp else {"positive": [], "negative": []}


__all__ = [
    "TextPreprocessor",
    "NLPAnalyzer",
    "SentimentModel",
    "SentimentResult",
    "MODEL_VERSION",
    "STATIC_DIR",
    "MODEL_DIR",
]
