"""
Aspect-Based Sentiment Analysis (ABSA).

WHY THIS EXISTS
---------------
The original implementation extracted (noun, adjective) pairs and stopped
there. "battery -> terrible" and "battery -> not terrible" produced identical
output, because polarity was never computed — the adjective was reported raw.
Worse, the extraction ignored the ``neg`` dependency entirely, so negated
opinions were reported as if they were affirmations. That is not a cosmetic
bug: it inverts the meaning of the result.

This module rebuilds that layer properly:

* aspects are **noun phrases**, not bare tokens, so "battery life" stays
  intact instead of being split into two unrelated features
* opinions attach through four syntactic routes (attributive, predicative,
  conjunction-propagated, and verb-mediated) rather than two
* every opinion is checked for **negation** on both the adjective and its
  governing verb, and the polarity is flipped accordingly
* comparatives and superlatives (``JJR``/``JJS``) are matched, so "worst" and
  "cheaper" finally register — the old ``tag_ == "JJ"`` test silently dropped
  them
* polarity is scored through the lexicon, so each aspect gets a signed value
  rather than an adjective string
* output ordering is **deterministic** (first-appearance order, deduplicated).
  The original used ``list({...})`` over a set, whose iteration order varies
  with PYTHONHASHSEED — the same review could render its features in a
  different order on each restart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from lexicon import INTENSIFIERS, NEGATION_SCALAR, LexiconSentiment

#: Fine-grained POS tags that denote a noun (aspect candidate).
NOUN_TAGS = frozenset({"NN", "NNS", "NNP", "NNPS"})

#: Adjective tags, including comparative and superlative forms.
ADJ_TAGS = frozenset({"JJ", "JJR", "JJS"})

#: Verbs that carry opinion directly ("the zipper broke", "the motor failed").
OPINION_VERB_LEMMAS = frozenset({
    "break", "fail", "stop", "die", "leak", "crack", "tear", "rip", "jam",
    "malfunction", "disappoint", "love", "hate", "enjoy", "regret", "recommend",
    "impress", "exceed", "last", "work",
})

#: Aspect heads not worth reporting — they are about the transaction or the
#: reviewer, not the product.
ASPECT_STOPLIST = frozenset({
    "thing", "things", "something", "anything", "nothing", "everything",
    "one", "ones", "lot", "lots", "bit", "kind", "sort", "way", "time",
    "times", "day", "days", "week", "weeks", "month", "months", "year",
    "years", "amazon", "product", "item", "purchase", "order", "review",
    "star", "stars", "money", "price",  # price handled as an aspect only via NP
})

POSITIVE_CUTOFF = 0.05
NEGATIVE_CUTOFF = -0.05


@dataclass
class AspectOpinion:
    """A single opinion expressed about a single aspect."""
    aspect: str
    opinion: str
    polarity: float           # normalised, in (-1, 1)
    label: str                # positive | negative | neutral
    negated: bool
    relation: str             # which syntactic route found this
    sentence: str = ""

    def as_dict(self) -> dict:
        return {
            "aspect": self.aspect,
            "opinion": self.opinion,
            "polarity": round(self.polarity, 4),
            "label": self.label,
            "negated": self.negated,
            "relation": self.relation,
            "sentence": self.sentence,
        }


@dataclass
class AspectAnalysis:
    """Everything the ABSA layer found in one review."""
    nouns: List[str] = field(default_factory=list)
    adjectives: List[str] = field(default_factory=list)
    opinions: List[AspectOpinion] = field(default_factory=list)

    @property
    def conflict_score(self) -> float:
        """How much the aspects disagree with each other, in [0, 1].

        A review saying "battery terrible, screen gorgeous" is far more
        informative than one saying "everything is fine", but a single
        positive/negative verdict flattens that distinction away. This score
        surfaces it: 0 means every aspect agrees, 1 means the review is
        maximally split.
        """
        if len(self.opinions) < 2:
            return 0.0
        pos = sum(1 for o in self.opinions if o.polarity > POSITIVE_CUTOFF)
        neg = sum(1 for o in self.opinions if o.polarity < NEGATIVE_CUTOFF)
        if pos + neg == 0:
            return 0.0
        # Normalised minority share: 0 when unanimous, 1 when evenly split.
        return round(2.0 * min(pos, neg) / (pos + neg), 4)

    @property
    def is_mixed(self) -> bool:
        return self.conflict_score >= 0.4

    def legacy_pairs(self) -> List[List[str]]:
        """(aspect, opinion) pairs in the original wire format.

        Kept so the existing Java DTO and React table keep working unchanged.
        """
        return [[o.aspect, o.opinion] for o in self.opinions]

    def as_dict(self) -> dict:
        return {
            "nouns": self.nouns,
            "adjectives": self.adjectives,
            "aspects": [o.as_dict() for o in self.opinions],
            "featureSentimentPairs": self.legacy_pairs(),
            "conflictScore": self.conflict_score,
            "isMixed": self.is_mixed,
        }


class AspectExtractor:
    """Dependency-driven aspect/opinion extraction with polarity."""

    def __init__(self, lexicon: LexiconSentiment | None = None):
        self.lexicon = lexicon or LexiconSentiment()

    # -- public -------------------------------------------------------------

    def analyze(self, doc) -> AspectAnalysis:
        """Extract aspects and opinions from a parsed spaCy ``Doc``."""
        nouns = self._dedupe(
            tok.text for tok in doc
            if tok.tag_ in NOUN_TAGS and not tok.is_stop
        )
        adjectives = self._dedupe(
            tok.text for tok in doc if tok.tag_ in ADJ_TAGS
        )

        opinions: List[AspectOpinion] = []
        seen: Set[Tuple[str, str]] = set()

        for token in doc:
            for aspect_tok, opinion_tok, relation in self._candidates(token):
                aspect = self._noun_phrase(aspect_tok)
                opinion = opinion_tok.text
                key = (aspect.lower(), opinion.lower())
                if key in seen:
                    continue
                if aspect_tok.lemma_.lower() in ASPECT_STOPLIST:
                    continue
                seen.add(key)

                negated = self._is_negated(opinion_tok)
                polarity = self._polarity(opinion_tok, negated)

                opinions.append(
                    AspectOpinion(
                        aspect=aspect,
                        opinion=opinion,
                        polarity=polarity,
                        label=self._label(polarity),
                        negated=negated,
                        relation=relation,
                        sentence=opinion_tok.sent.text.strip(),
                    )
                )

        return AspectAnalysis(nouns=nouns, adjectives=adjectives, opinions=opinions)

    # -- candidate discovery ------------------------------------------------

    def _candidates(self, token) -> Iterable[Tuple[object, object, str]]:
        """Yield (aspect_token, opinion_token, relation) triples for one token."""

        # 1. Attributive: "the terrible battery"
        #    The adjective modifies the noun directly.
        if token.dep_ == "amod" and token.tag_ in ADJ_TAGS and token.head.tag_ in NOUN_TAGS:
            yield token.head, token, "amod"

            # 1b. Conjunction propagation: "the terrible battery and screen".
            #     The old code missed this entirely — only the first noun in a
            #     coordinated list ever received the opinion.
            for sibling in token.head.conjuncts:
                if sibling.tag_ in NOUN_TAGS:
                    yield sibling, token, "amod+conj"

        # 2. Predicative: "the battery is terrible"
        #    Adjective and noun are siblings under the copula, so we walk up to
        #    the verb and back down to its subject.
        if token.dep_ == "acomp" and token.tag_ in ADJ_TAGS:
            for child in token.head.children:
                if child.dep_ in ("nsubj", "nsubjpass") and child.tag_ in NOUN_TAGS:
                    yield child, token, "acomp"
                    for sibling in child.conjuncts:
                        if sibling.tag_ in NOUN_TAGS:
                            yield sibling, token, "acomp+conj"

            # 2b. Coordinated adjectives: "the battery is terrible and noisy".
            for conj in token.conjuncts:
                if conj.tag_ in ADJ_TAGS:
                    for child in token.head.children:
                        if child.dep_ in ("nsubj", "nsubjpass") and child.tag_ in NOUN_TAGS:
                            yield child, conj, "acomp+adjconj"

        # 3. Verb-mediated: "the zipper broke", "the motor failed"
        #    No adjective involved at all; the verb is the opinion.
        if token.pos_ == "VERB" and token.lemma_.lower() in OPINION_VERB_LEMMAS:
            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass") and child.tag_ in NOUN_TAGS:
                    yield child, token, "verb"

        # 4. Object-of-opinion: "I love the battery", "I hate the packaging"
        if token.pos_ == "VERB" and token.lemma_.lower() in OPINION_VERB_LEMMAS:
            for child in token.children:
                if child.dep_ in ("dobj", "obj") and child.tag_ in NOUN_TAGS:
                    yield child, token, "dobj"

    # -- polarity -----------------------------------------------------------

    def _polarity(self, opinion_tok, negated: bool) -> float:
        """Score one opinion word, applying negation and degree."""
        word = opinion_tok.lemma_.lower()
        base = self.lexicon.valence.get(word)

        if base is None:
            base = self.lexicon.valence.get(opinion_tok.text.lower())

        if base is None:
            # Superlatives and comparatives often aren't in the lexicon in their
            # inflected form ("worst" vs "bad"); the lemma usually is, which is
            # why we tried lemma first. If still unknown, fall back to scoring
            # the whole clause so we return something calibrated rather than 0.
            span = opinion_tok.sent.text
            score = self.lexicon.score(span).compound
            return round(score, 4)

        # Superlatives intensify.
        if opinion_tok.tag_ == "JJS":
            base *= 1.3
        elif opinion_tok.tag_ == "JJR":
            base *= 1.1

        # Intensifier attached as an adverbial modifier ("very good").
        for child in opinion_tok.children:
            if child.dep_ == "advmod":
                scalar = INTENSIFIERS.get(child.lemma_.lower())
                if scalar:
                    base += scalar * (1 if base > 0 else -1)

        if negated:
            base *= NEGATION_SCALAR

        # Normalise onto the same (-1, 1) scale the document score uses.
        return round(base / ((base * base + 15.0) ** 0.5), 4)

    @staticmethod
    def _is_negated(token) -> bool:
        """True when the opinion is negated, directly or via its governor.

        Covers both "the battery is *not* terrible" (neg on the copula) and
        "a *not* terrible battery" (neg on the adjective itself).
        """
        for child in token.children:
            if child.dep_ == "neg":
                return True
            # spaCy tags some negators as advmod rather than neg.
            if child.dep_ == "advmod" and child.lemma_.lower() in ("not", "never", "n't"):
                return True

        head = token.head
        if head is not token:
            for child in head.children:
                if child.dep_ == "neg":
                    return True
                if child.dep_ == "advmod" and child.lemma_.lower() in ("not", "never", "n't"):
                    return True
        return False

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _noun_phrase(token) -> str:
        """Expand a noun to its compound phrase: "life" -> "battery life"."""
        parts = [c for c in token.children if c.dep_ == "compound"]
        if not parts:
            return token.text
        parts.append(token)
        parts.sort(key=lambda t: t.i)
        return " ".join(t.text for t in parts)

    @staticmethod
    def _label(polarity: float) -> str:
        if polarity >= POSITIVE_CUTOFF:
            return "positive"
        if polarity <= NEGATIVE_CUTOFF:
            return "negative"
        return "neutral"

    @staticmethod
    def _dedupe(items: Iterable[str]) -> List[str]:
        """Deduplicate while preserving first-appearance order.

        ``dict.fromkeys`` keeps insertion order in Python 3.7+, unlike the
        ``set`` the original code used — whose iteration order depends on hash
        randomisation and therefore changed between process restarts.
        """
        return list(dict.fromkeys(items))


__all__ = [
    "AspectExtractor",
    "AspectAnalysis",
    "AspectOpinion",
    "NOUN_TAGS",
    "ADJ_TAGS",
]
