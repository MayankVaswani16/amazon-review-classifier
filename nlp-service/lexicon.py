"""
Rule-based sentiment lexicon for product-review text.

WHY THIS EXISTS
---------------
A TF-IDF + Logistic Regression classifier can only score words it saw during
training. Feed it a review made entirely of unseen vocabulary and
`vectorizer.transform` produces an all-zero row, so the prediction collapses to
the model's intercept — a confident-looking answer derived from no evidence at
all. That is the single biggest real-world failure mode of the original
pipeline.

This module is the antidote: a valence lexicon plus the compositional rules that
actually decide polarity in English review text (negation scope, intensifiers,
contrastive conjunctions, emphasis). It has no training data requirement, so it
degrades gracefully on vocabulary the classifier has never encountered, and it
gets negation right by construction rather than by hoping the bigram
"not_good" appeared often enough in training.

The scoring rules follow the design of VADER (Hutto & Gilbert, 2014) —
valence-shifting with a damped negation multiplier and additive intensifier
boosts — reimplemented here so the service has zero extra dependencies and no
runtime corpus download.

Everything is deterministic: same input, same score, always.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Tuning constants (VADER-derived, kept explicit so they can be justified)
# ---------------------------------------------------------------------------

#: Negation does not simply flip polarity — "not great" is milder than "awful".
#: Empirically a damped flip around -0.74 models this better than -1.0.
NEGATION_SCALAR = -0.74

#: How far back from a sentiment word we look for a negator. Three tokens
#: covers "not very good", "isn't really great", "never a good buy".
NEGATION_WINDOW = 3

#: Additive boost applied by an intensifier immediately preceding the term.
#: Decays with distance so "very extremely good" doesn't double-count fully.
INTENSIFIER_DECAY = (1.0, 0.95, 0.90)

#: Emphasis boosts.
ALLCAPS_BOOST = 0.733
EXCLAMATION_BOOST = 0.292
MAX_EXCLAMATIONS = 4
QUESTION_DAMPEN = 0.96

#: Words after a contrastive conjunction carry the writer's real point.
CONTRAST_BEFORE_WEIGHT = 0.5
CONTRAST_AFTER_WEIGHT = 1.5

#: Normalisation constant: score / sqrt(score^2 + ALPHA) maps R -> (-1, 1).
ALPHA = 15.0

#: Decision thresholds on the normalised compound score.
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05


# ---------------------------------------------------------------------------
# Valence lexicon — tuned for e-commerce product reviews
# ---------------------------------------------------------------------------
# Scale: -4 (most negative) .. +4 (most positive).
# Chosen for review vocabulary specifically: generic sentiment lexicons
# under-weight commerce terms like "refund", "counterfeit", "overpriced".

_POSITIVE: Dict[str, float] = {
    # strong praise
    "amazing": 3.4, "excellent": 3.4, "outstanding": 3.4, "perfect": 3.5,
    "fantastic": 3.3, "superb": 3.3, "flawless": 3.4, "exceptional": 3.3,
    "incredible": 3.2, "phenomenal": 3.4, "brilliant": 3.2, "wonderful": 3.2,
    "awesome": 3.1, "stellar": 3.1, "terrific": 3.0, "magnificent": 3.2,
    "marvelous": 3.1, "spectacular": 3.2, "impeccable": 3.3, "sublime": 3.1,
    "best": 3.2, "gem": 2.9, "masterpiece": 3.3, "unbeatable": 3.0,
    "love": 3.0, "loved": 3.0, "loves": 2.9, "adore": 3.0, "delighted": 2.9,
    "thrilled": 2.9, "ecstatic": 3.1, "overjoyed": 3.0,
    # moderate praise
    # NOTE: aspect nouns ("quality", "price", "design") are deliberately absent.
    # They carry no polarity of their own and including them wrecks composition:
    # with quality=+1.6, "cheap quality" scored ~0 instead of clearly negative.
    # Polarity belongs to the opinion word; the noun is the *target*, which the
    # ABSA layer in aspects.py handles separately.
    "great": 2.6, "good": 1.9, "nice": 1.8, "solid": 1.9,
    "happy": 2.2, "pleased": 2.1, "satisfied": 2.0, "satisfying": 2.1,
    "reliable": 2.2, "dependable": 2.2, "sturdy": 2.0, "durable": 2.2,
    "robust": 2.0, "comfortable": 2.0, "cozy": 1.9, "sleek": 2.0,
    "smooth": 1.8, "seamless": 2.1, "responsive": 1.9, "crisp": 1.8,
    "vibrant": 2.0, "bright": 1.5, "sharp": 1.6, "clear": 1.4,
    "fast": 1.7, "quick": 1.6, "speedy": 1.7, "efficient": 2.0,
    "easy": 1.8, "effortless": 2.1, "intuitive": 2.0, "convenient": 1.8,
    "helpful": 2.0, "useful": 1.9, "practical": 1.7, "versatile": 1.8,
    "worth": 1.9, "worthwhile": 2.0, "bargain": 2.2, "affordable": 1.7,
    "recommend": 2.4, "recommended": 2.3, "impressed": 2.4,
    "impressive": 2.4, "premium": 2.0, "luxurious": 2.2, "elegant": 2.1,
    "beautiful": 2.5, "gorgeous": 2.7, "stylish": 2.0, "attractive": 1.9,
    "generous": 1.8, "spacious": 1.6, "lightweight": 1.3, "portable": 1.4,
    "powerful": 1.8, "accurate": 1.8, "precise": 1.8, "consistent": 1.6,
    "genuine": 1.7, "authentic": 1.8, "professional": 1.6, "polished": 1.8,
    "exceeded": 2.6, "exceeds": 2.5, "surpassed": 2.5,
    "works": 1.2, "working": 1.1, "functional": 1.2, "performs": 1.2,
    "enjoy": 2.2, "enjoyed": 2.2, "enjoying": 2.2, "enjoyable": 2.2,
    "glad": 2.0, "grateful": 2.1, "appreciate": 1.9, "favorite": 2.4,
    "favourite": 2.4, "charm": 2.0, "delight": 2.6,
    "recommendable": 2.1, "keeper": 2.0,
    # mild / hedged positives
    "okay": 0.7, "ok": 0.7, "fine": 0.9, "decent": 1.2, "adequate": 0.8,
    "acceptable": 0.8, "fair": 0.8, "reasonable": 1.2, "alright": 0.7,
    "passable": 0.5, "serviceable": 0.7, "sufficient": 0.8,
}

_NEGATIVE: Dict[str, float] = {
    # strong condemnation
    "terrible": -3.4, "awful": -3.3, "horrible": -3.4, "horrid": -3.3,
    "atrocious": -3.5, "appalling": -3.4, "abysmal": -3.5, "dreadful": -3.3,
    "worst": -3.5, "garbage": -3.3, "junk": -3.1, "trash": -3.2,
    "rubbish": -3.0, "useless": -3.0, "worthless": -3.2, "unusable": -3.1,
    "disaster": -3.2, "nightmare": -3.1, "catastrophe": -3.3,
    "scam": -3.6, "fraud": -3.6, "fraudulent": -3.5, "counterfeit": -3.4,
    "ripoff": -3.4, "swindle": -3.3, "hate": -3.0, "hated": -3.0,
    "regret": -2.8, "regretted": -2.8, "abomination": -3.4,
    "unacceptable": -2.9, "inexcusable": -3.0, "deplorable": -3.1,
    # moderate criticism
    "bad": -2.3, "poor": -2.3, "poorly": -2.3, "cheap": -1.8,
    "cheaply": -2.0, "flimsy": -2.4, "fragile": -1.9, "brittle": -2.0,
    "shoddy": -2.6, "sloppy": -2.3, "crude": -1.9, "clunky": -2.0,
    "bulky": -1.4, "heavy": -1.0, "awkward": -1.6, "uncomfortable": -2.0,
    "slow": -1.8, "sluggish": -2.0, "laggy": -2.1, "unresponsive": -2.3,
    "difficult": -1.7, "confusing": -1.9, "complicated": -1.5,
    "frustrating": -2.4, "frustrated": -2.3, "annoying": -2.2,
    "irritating": -2.2, "disappointing": -2.5, "disappointed": -2.5,
    "disappointment": -2.5, "underwhelming": -2.0, "mediocre": -1.7,
    "bland": -1.4, "boring": -1.5, "dull": -1.4, "meh": -1.2,
    "lacking": -1.7, "lacks": -1.6, "missing": -1.8, "incomplete": -1.9,
    "defective": -2.9, "faulty": -2.8, "broken": -2.8, "broke": -2.7,
    "damaged": -2.6, "cracked": -2.4, "scratched": -1.9, "dented": -2.0,
    "malfunction": -2.7, "malfunctioning": -2.7, "glitchy": -2.2,
    "buggy": -2.2, "unreliable": -2.6, "inconsistent": -1.8,
    "overpriced": -2.4, "expensive": -1.3, "pricey": -1.2, "costly": -1.3,
    "late": -1.6, "delayed": -1.7, "slowly": -1.4,
    "refund": -1.6, "complaint": -1.9,
    "unhappy": -2.3, "unsatisfied": -2.3, "dissatisfied": -2.4,
    "misleading": -2.5, "deceptive": -2.7, "dishonest": -2.8,
    "unhelpful": -2.1, "rude": -2.5, "ignored": -2.0, "neglected": -2.0,
    "waste": -2.6, "wasted": -2.6, "avoid": -2.4, "beware": -2.3,
    "fails": -2.4, "failed": -2.4, "failure": -2.5,
    "died": -2.4, "dead": -2.3, "leaks": -2.2,
    "leaking": -2.2, "noisy": -1.7, "smelly": -2.0,
    "dirty": -1.8, "stained": -1.7, "worn": -1.4, "faded": -1.5,
    "flaw": -1.9, "flawed": -2.1,
    "defect": -2.5, "issue": -1.4, "issues": -1.5, "problem": -1.7,
    "problems": -1.8, "trouble": -1.7, "error": -1.6, "errors": -1.7,
    "hassle": -1.8, "nuisance": -1.8, "letdown": -2.4, "shame": -1.6,
    "sadly": -1.3, "unfortunately": -1.4, "meh": -1.2, "bummer": -1.6,
}

VALENCE: Dict[str, float] = {**_POSITIVE, **_NEGATIVE}

# Multi-word expressions whose meaning is not the sum of their parts.
# Checked before single tokens so "not worth" doesn't get scored as
# negate(worth) — the idiom is stronger than the composition.
PHRASES: Dict[str, float] = {
    "not worth": -2.6,
    "waste of money": -3.2,
    "waste of time": -2.9,
    "save your money": -2.9,
    "do not buy": -3.2,
    "dont buy": -3.0,
    "don't buy": -3.0,
    "would not recommend": -2.8,
    "wouldn't recommend": -2.8,
    "not recommend": -2.7,
    "no longer works": -2.8,
    "stopped working": -2.8,
    "fell apart": -2.9,
    "falls apart": -2.9,
    "money back": -1.8,
    "never again": -2.7,
    "highly recommend": 2.9,
    "would recommend": 2.5,
    "worth every penny": 3.0,
    "worth it": 2.2,
    "value for money": 2.3,
    "works great": 2.7,
    "works perfectly": 3.0,
    "works well": 2.2,
    "as described": 1.5,
    "as advertised": 1.5,
    "better than expected": 2.7,
    "exceeded expectations": 2.9,
    "no complaints": 1.9,
    "no issues": 1.8,
    "no problems": 1.8,
    "not bad": 1.1,
    "not great": -1.3,
    "not good": -1.7,
    "not happy": -2.0,
    "buy again": 2.2,
    "five stars": 2.8,
    "one star": -2.8,
    "hit or miss": -1.0,
    # Ambiguous single words promoted to phrases so the surrounding words
    # disambiguate them. "returns" alone is neutral ("free returns" is a perk);
    # "had to return" is not.
    "had to return": -2.2,
    "returned it": -2.0,
    "sent it back": -2.1,
    "poor quality": -2.6,
    "cheap quality": -2.4,
    "low quality": -2.4,
    "great quality": 2.6,
    "excellent quality": 3.0,
    "good quality": 2.0,
    "build quality": 0.0,
    "heavy duty": 1.5,
    "a steal": 2.2,
    "well made": 2.3,
    "poorly made": -2.6,
    "well built": 2.3,
    "cheaply made": -2.6,
    "arrived damaged": -2.8,
    "arrived broken": -2.9,
    "on time": 1.4,
    "customer service": 0.0,
    # Review English leans heavily on idiom rather than adjectives. Without
    # these the lexicon abstained on ~40% of realistic reviews, which is the
    # same as having no lexicon at all on those inputs.
    "rip off": -3.4,
    "ripped off": -3.2,
    "does the job": 1.6,
    "did the job": 1.6,
    "does exactly what": 2.0,
    "can't fault": 2.4,
    "cant fault": 2.4,
    "cannot fault": 2.4,
    "going strong": 2.2,
    "gave up": -2.4,
    "packed up": -2.2,
    "stopped charging": -2.6,
    "in the bin": -2.8,
    "in the trash": -2.8,
    "money well spent": 2.8,
    "well spent": 2.5,
    "worse than": -2.0,
    "better than": 2.0,
    "snapped off": -2.6,
    "fell off": -2.3,
    "would buy again": 2.5,
    "wouldn't hesitate": 2.4,
    "zero problems": 2.2,
    "no problem": 1.7,
    "nothing wrong": 1.9,
    "nothing special": -0.9,
    "not impressed": -2.2,
    "look elsewhere": -2.4,
    "as expected": 1.3,
    "as promised": 1.6,
    "never see again": -2.4,
    "partial refund": -1.8,
    "still works": 1.8,
    "no longer": -1.4,
}

INTENSIFIERS: Dict[str, float] = {
    # amplifiers
    "very": 0.293, "really": 0.293, "extremely": 0.500, "incredibly": 0.500,
    "absolutely": 0.400, "completely": 0.350, "totally": 0.330,
    "utterly": 0.420, "highly": 0.320, "super": 0.330, "so": 0.250,
    "too": 0.220, "quite": 0.180, "remarkably": 0.420, "exceptionally": 0.480,
    "particularly": 0.280, "especially": 0.290, "truly": 0.320,
    "seriously": 0.310, "insanely": 0.480, "ridiculously": 0.450,
    "amazingly": 0.440, "surprisingly": 0.300, "unbelievably": 0.460,
    "damn": 0.380, "freaking": 0.400, "incredibly": 0.500,
    # downtoners (negative boost = weaken)
    "slightly": -0.293, "somewhat": -0.293, "kind": -0.250, "kinda": -0.280,
    "sort": -0.250, "sorta": -0.280, "barely": -0.400, "hardly": -0.400,
    "marginally": -0.350, "fairly": -0.150, "rather": -0.120,
    "mildly": -0.320, "partially": -0.300, "occasionally": -0.280,
    "little": -0.250, "bit": -0.280,
}

NEGATORS: Set[str] = {
    "not", "no", "never", "none", "nobody", "nothing", "nowhere", "neither",
    "nor", "cannot", "cant", "can't", "wont", "won't", "dont", "don't",
    "doesnt", "doesn't", "didnt", "didn't", "isnt", "isn't", "arent",
    "aren't", "wasnt", "wasn't", "werent", "weren't", "hasnt", "hasn't",
    "havent", "haven't", "hadnt", "hadn't", "shouldnt", "shouldn't",
    "wouldnt", "wouldn't", "couldnt", "couldn't", "without", "lack",
    "lacks", "lacking", "rarely", "seldom", "hardly", "barely",
}

CONTRASTIVE: Set[str] = {
    "but", "however", "although", "though", "yet", "except", "unfortunately",
    "nevertheless", "nonetheless", "whereas", "still",
}

_TOKEN_RE = re.compile(r"[A-Za-z']+|[!?]+")
_WORD_RE = re.compile(r"^[A-Za-z']+$")


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class TokenValence:
    """One token's contribution to the final sentiment score."""
    token: str
    index: int
    base: float            # raw lexicon valence
    value: float           # valence after all rules
    negated: bool = False
    intensified: bool = False

    def as_dict(self) -> dict:
        return {
            "token": self.token,
            "index": self.index,
            "base": round(self.base, 3),
            "value": round(self.value, 3),
            "negated": self.negated,
            "intensified": self.intensified,
        }


@dataclass
class LexiconScore:
    """Full result of scoring one piece of text."""
    compound: float                      # normalised, in (-1, 1)
    positive_sum: float
    negative_sum: float
    label: str                           # positive | negative | neutral
    tokens: List[TokenValence] = field(default_factory=list)
    matched_phrases: List[str] = field(default_factory=list)

    @property
    def has_signal(self) -> bool:
        """True when at least one sentiment-bearing term was found."""
        return bool(self.tokens) or bool(self.matched_phrases)

    def as_dict(self) -> dict:
        return {
            "compound": round(self.compound, 4),
            "positive": round(self.positive_sum, 3),
            "negative": round(self.negative_sum, 3),
            "label": self.label,
            "hasSignal": self.has_signal,
            "tokens": [t.as_dict() for t in self.tokens],
            "phrases": self.matched_phrases,
        }


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class LexiconSentiment:
    """Deterministic rule-based sentiment scorer for review text.

    Usage:
        >>> lex = LexiconSentiment()
        >>> lex.score("The battery is not great but the screen is gorgeous").label
        'positive'
    """

    def __init__(
        self,
        valence: Dict[str, float] | None = None,
        phrases: Dict[str, float] | None = None,
    ):
        self.valence = dict(valence if valence is not None else VALENCE)
        self.phrases = dict(phrases if phrases is not None else PHRASES)
        # Longest phrases first so "waste of money" wins over "waste".
        self._phrase_order = sorted(self.phrases, key=len, reverse=True)

    # -- public API ---------------------------------------------------------

    def score(self, text: str) -> LexiconScore:
        """Score a piece of text, returning the compound value and per-token detail."""
        if not text or not text.strip():
            return LexiconScore(0.0, 0.0, 0.0, "neutral")

        lowered = text.lower()
        raw_tokens = _TOKEN_RE.findall(text)
        words = [t for t in raw_tokens if _WORD_RE.match(t)]
        lower_words = [w.lower() for w in words]

        # --- multi-word idioms ------------------------------------------
        phrase_total = 0.0
        matched: List[str] = []
        consumed: Set[int] = set()
        for phrase in self._phrase_order:
            if phrase not in lowered:
                continue
            span = self._locate(lower_words, phrase)
            if span is None:
                continue
            start, end = span
            if any(i in consumed for i in range(start, end)):
                continue
            consumed.update(range(start, end))
            phrase_total += self.phrases[phrase]
            matched.append(phrase)

        # --- contrastive conjunction split ------------------------------
        contrast_at = next(
            (i for i, w in enumerate(lower_words) if w in CONTRASTIVE), None
        )

        # --- single tokens ----------------------------------------------
        token_scores: List[TokenValence] = []
        for i, word in enumerate(lower_words):
            if i in consumed or word not in self.valence:
                continue

            base = self.valence[word]
            value = base
            intensified = False

            # Intensifiers looking backwards, with distance decay.
            for dist, back in enumerate(range(i - 1, max(-1, i - 4), -1)):
                if back < 0:
                    break
                booster = INTENSIFIERS.get(lower_words[back])
                if booster is None:
                    continue
                scalar = booster * INTENSIFIER_DECAY[min(dist, 2)]
                # An amplifier pushes away from zero; a downtoner pulls toward it.
                value += scalar if value > 0 else -scalar
                intensified = True

            # ALL-CAPS emphasis on the original (non-lowered) token.
            if words[i].isupper() and len(words[i]) > 1:
                value += ALLCAPS_BOOST if value > 0 else -ALLCAPS_BOOST

            # Negation within the lookback window.
            negated = self._is_negated(lower_words, i)
            if negated:
                value *= NEGATION_SCALAR

            # Contrastive weighting.
            if contrast_at is not None:
                value *= (
                    CONTRAST_BEFORE_WEIGHT if i < contrast_at
                    else CONTRAST_AFTER_WEIGHT
                )

            token_scores.append(
                TokenValence(
                    token=words[i], index=i, base=base, value=value,
                    negated=negated, intensified=intensified,
                )
            )

        total = phrase_total + sum(t.value for t in token_scores)

        # Punctuation emphasis.
        total = self._apply_punctuation(total, text)

        pos_sum = sum(t.value for t in token_scores if t.value > 0)
        pos_sum += sum(v for p, v in ((p, self.phrases[p]) for p in matched) if v > 0)
        neg_sum = sum(t.value for t in token_scores if t.value < 0)
        neg_sum += sum(v for p, v in ((p, self.phrases[p]) for p in matched) if v < 0)

        compound = self._normalise(total)
        label = (
            "positive" if compound >= POSITIVE_THRESHOLD
            else "negative" if compound <= NEGATIVE_THRESHOLD
            else "neutral"
        )

        return LexiconScore(
            compound=compound,
            positive_sum=pos_sum,
            negative_sum=neg_sum,
            label=label,
            tokens=token_scores,
            matched_phrases=matched,
        )

    def polarity_of(self, words: Sequence[str]) -> float:
        """Compound polarity of a short span — used for aspect-level scoring."""
        return self.score(" ".join(words)).compound

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _locate(words: List[str], phrase: str) -> Tuple[int, int] | None:
        """Find a whitespace-delimited phrase in the token list. Returns [start, end)."""
        parts = phrase.split()
        n = len(parts)
        if n == 0 or n > len(words):
            return None
        for i in range(len(words) - n + 1):
            if words[i:i + n] == parts:
                return i, i + n
        return None

    @staticmethod
    def _is_negated(words: Sequence[str], idx: int) -> bool:
        """Look back up to NEGATION_WINDOW tokens for a negator."""
        start = max(0, idx - NEGATION_WINDOW)
        return any(w in NEGATORS for w in words[start:idx])

    @staticmethod
    def _apply_punctuation(total: float, text: str) -> float:
        """Exclamation marks amplify; question marks slightly dampen certainty."""
        if total == 0.0:
            return total
        bangs = min(text.count("!"), MAX_EXCLAMATIONS)
        if bangs:
            boost = bangs * EXCLAMATION_BOOST
            total += boost if total > 0 else -boost
        if "?" in text:
            total *= QUESTION_DAMPEN
        return total

    @staticmethod
    def _normalise(score: float) -> float:
        """Map an unbounded sum into (-1, 1)."""
        if score == 0.0:
            return 0.0
        norm = score / ((score * score + ALPHA) ** 0.5)
        return max(-1.0, min(1.0, norm))


__all__ = [
    "LexiconSentiment",
    "LexiconScore",
    "TokenValence",
    "VALENCE",
    "PHRASES",
    "NEGATORS",
    "INTENSIFIERS",
    "CONTRASTIVE",
    "POSITIVE_THRESHOLD",
    "NEGATIVE_THRESHOLD",
]
