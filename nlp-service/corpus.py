"""
Training corpus for the sentiment classifier.

WHY THIS EXISTS
---------------
The original service trained on 100 hand-written sentences in which every
positive contained "amazing"/"excellent" and every negative contained
"terrible"/"awful". The two classes were lexically disjoint, so the reported
test accuracy was ~100% and told you nothing: the model had memorised a word
list, and any real review with mixed sentiment, negation, or ordinary
vocabulary would be classified essentially at random.

This module fixes the data, which is the only fix that matters for real-world
accuracy. Two sources, in priority order:

1. A **real dataset**, if one is available (``DATASET_PATH`` env var, or
   ``data/reviews.csv``). This is what you should use in production — point it
   at Amazon Reviews, Amazon Fine Food Reviews, or your own labelled data.

2. A **generated corpus** otherwise, so the service boots with zero
   configuration and no network access. Unlike the old 100 samples this is
   built to be genuinely *hard*:

   * ~4,000 reviews composed from aspect/opinion/template grammars
   * deliberate **vocabulary overlap** between classes — negative reviews
     contain positive words under negation ("not worth it", "isn't great")
     and positive reviews contain hedged criticism ("a little pricey, but")
   * **mixed-polarity** reviews where the minority sentiment is present and
     the label follows the dominant one
   * neutral filler sentences carrying no polarity at all
   * a realistic **70/30 positive/negative skew**, matching observed
     e-commerce rating distributions — which also means SMOTE finally has a
     genuine imbalance to correct instead of being a no-op on 50/50 data

The generator is seeded, so the corpus is byte-identical on every run and
training is reproducible.
"""

from __future__ import annotations

import csv
import logging
import os
import random
from typing import List, Sequence, Tuple

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DEFAULT_CSV = os.path.join(DATA_DIR, "reviews.csv")

#: Observed e-commerce review distributions skew strongly positive.
POSITIVE_RATIO = 0.70
DEFAULT_SIZE = 4000
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

ASPECTS: Sequence[str] = (
    "battery life", "battery", "screen", "display", "camera", "sound quality",
    "audio", "speaker", "build quality", "design", "material", "fabric",
    "stitching", "zipper", "packaging", "shipping", "delivery", "price",
    "value", "customer service", "support", "instructions", "manual",
    "setup", "installation", "app", "software", "interface", "buttons",
    "keyboard", "touchpad", "charger", "cable", "adapter", "fit", "size",
    "weight", "colour", "finish", "motor", "blade", "filter", "lid",
    "handle", "strap", "case", "screen protector", "warranty", "return policy",
)

POSITIVE_ADJ: Sequence[str] = (
    "excellent", "outstanding", "fantastic", "superb", "solid", "reliable",
    "sturdy", "durable", "comfortable", "responsive", "crisp", "vibrant",
    "sleek", "elegant", "gorgeous", "impressive", "generous", "accurate",
    "smooth", "seamless", "intuitive", "convenient", "practical", "premium",
    "beautiful", "flawless", "quick", "efficient", "helpful", "affordable",
)

NEGATIVE_ADJ: Sequence[str] = (
    "terrible", "awful", "flimsy", "cheap", "shoddy", "unreliable", "clunky",
    "sluggish", "unresponsive", "uncomfortable", "confusing", "frustrating",
    "disappointing", "mediocre", "defective", "faulty", "overpriced",
    "misleading", "useless", "noisy", "fragile", "sloppy", "underwhelming",
    "inconsistent", "unhelpful", "poor", "broken", "damaged", "worthless",
)

NEUTRAL_ADJ: Sequence[str] = (
    "standard", "typical", "average", "ordinary", "basic", "plain",
    "regular", "usual", "simple", "compact",
)

INTENSIFIERS: Sequence[str] = (
    "very", "really", "extremely", "incredibly", "absolutely", "quite",
    "genuinely", "surprisingly", "remarkably",
)

HEDGES: Sequence[str] = (
    "a little", "somewhat", "slightly", "a bit", "kind of", "fairly",
)

POSITIVE_TEMPLATES: Sequence[str] = (
    "the {aspect} is {intensifier} {pos}",
    "{intensifier} {pos} {aspect}",
    "i love the {aspect}",
    "the {aspect} works {pos}ly well",
    "really pleased with the {aspect}",
    "the {aspect} exceeded my expectations",
    "no complaints about the {aspect}",
    "the {aspect} is exactly as described",
    "great {aspect} for the money",
    "the {aspect} has been {pos} so far",
    "you can tell the {aspect} is {pos}",
    "worth it just for the {aspect}",
    "the {aspect} alone makes this worth buying",
    "honestly the {aspect} is better than i expected",
)

NEGATIVE_TEMPLATES: Sequence[str] = (
    "the {aspect} is {intensifier} {neg}",
    "{intensifier} {neg} {aspect}",
    "i hate the {aspect}",
    "the {aspect} stopped working after a week",
    "very disappointed with the {aspect}",
    "the {aspect} did not last",
    "the {aspect} is not worth the price",
    "the {aspect} is nothing like the description",
    "would not recommend because of the {aspect}",
    "the {aspect} arrived damaged",
    "had to return it because of the {aspect}",
    "the {aspect} failed within days",
    "save your money, the {aspect} is {neg}",
    "the {aspect} is a complete waste of money",
)

#: Negative sentences built from POSITIVE vocabulary under negation.
#: These are what force the model to learn negation instead of keyword spotting.
NEGATED_POSITIVE_TEMPLATES: Sequence[str] = (
    "the {aspect} is not {pos} at all",
    "the {aspect} is not {intensifier} {pos}",
    "i would not call the {aspect} {pos}",
    "the {aspect} is far from {pos}",
    "do not expect the {aspect} to be {pos}",
    "the {aspect} is anything but {pos}",
    "never had a {pos} experience with the {aspect}",
    "the {aspect} is hardly {pos}",
)

#: Positive sentences built from NEGATIVE vocabulary under negation.
NEGATED_NEGATIVE_TEMPLATES: Sequence[str] = (
    "the {aspect} is not {neg} at all",
    "nothing {neg} about the {aspect}",
    "the {aspect} is not as {neg} as the reviews said",
    "i did not find the {aspect} {neg}",
    "no {neg} surprises with the {aspect}",
)

#: Hedged criticism that appears inside otherwise-positive reviews.
MILD_COMPLAINT_TEMPLATES: Sequence[str] = (
    "the {aspect} is {hedge} {neg}",
    "the {aspect} could be better",
    "i wish the {aspect} was different",
    "the {aspect} took some getting used to",
    "the only downside is the {aspect}",
)

#: Hedged praise that appears inside otherwise-negative reviews.
MILD_PRAISE_TEMPLATES: Sequence[str] = (
    "the {aspect} is {hedge} {pos}",
    "at least the {aspect} is fine",
    "the {aspect} is the one good part",
    "i will give it credit for the {aspect}",
)

NEUTRAL_TEMPLATES: Sequence[str] = (
    "i bought this last month",
    "it arrived on a tuesday",
    "this is my second one",
    "i use it every day",
    "the {aspect} is {neutral}",
    "i ordered it for my family",
    "it comes in a small box",
    "there is a {neutral} {aspect}",
    "i have been using it for a few weeks",
    "the box contained the usual accessories",
)

CONTRAST_CONNECTIVES: Sequence[str] = (
    "but", "although", "however", "that said", "even so",
)

CLOSERS_POSITIVE: Sequence[str] = (
    "would buy again", "highly recommend", "five stars",
    "very happy with this purchase", "no regrets", "worth every penny",
)

CLOSERS_NEGATIVE: Sequence[str] = (
    "would not buy again", "do not recommend", "one star",
    "very unhappy with this purchase", "total waste of money",
    "look elsewhere",
)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class ReviewCorpusGenerator:
    """Builds a synthetic but non-trivial review corpus.

    The point is deliberate class overlap. A model that simply memorises
    "terrible -> negative" will score poorly here, because ~25% of negative
    reviews contain no negative adjective at all (they use negated positives)
    and ~30% of positive reviews contain an explicit complaint.
    """

    def __init__(self, seed: int = RANDOM_SEED):
        self.rng = random.Random(seed)

    # -- sentence builders --------------------------------------------------

    def _fill(self, template: str) -> str:
        return template.format(
            aspect=self.rng.choice(ASPECTS),
            pos=self.rng.choice(POSITIVE_ADJ),
            neg=self.rng.choice(NEGATIVE_ADJ),
            neutral=self.rng.choice(NEUTRAL_ADJ),
            intensifier=self.rng.choice(INTENSIFIERS),
            hedge=self.rng.choice(HEDGES),
        )

    def _positive_sentence(self) -> str:
        pool = (
            POSITIVE_TEMPLATES * 3          # mostly plain praise
            + NEGATED_NEGATIVE_TEMPLATES    # praise via negated criticism
        )
        return self._fill(self.rng.choice(pool))

    def _negative_sentence(self) -> str:
        pool = (
            NEGATIVE_TEMPLATES * 3          # mostly plain criticism
            + NEGATED_POSITIVE_TEMPLATES * 2  # criticism via negated praise
        )
        return self._fill(self.rng.choice(pool))

    def _neutral_sentence(self) -> str:
        return self._fill(self.rng.choice(NEUTRAL_TEMPLATES))

    # -- review builders ----------------------------------------------------

    def _positive_review(self) -> str:
        parts: List[str] = [self._positive_sentence()]

        if self.rng.random() < 0.35:
            parts.append(self._neutral_sentence())

        parts.append(self._positive_sentence())

        # ~30% of positive reviews carry a real complaint. This is what stops
        # the classifier assuming any negative word implies a negative review.
        if self.rng.random() < 0.30:
            complaint = self._fill(self.rng.choice(MILD_COMPLAINT_TEMPLATES))
            connective = self.rng.choice(CONTRAST_CONNECTIVES)
            parts.append(f"{connective} {complaint}")
            # The contrast then resolves back to positive.
            parts.append(self._positive_sentence())

        if self.rng.random() < 0.55:
            parts.append(self.rng.choice(CLOSERS_POSITIVE))

        return self._join(parts)

    def _negative_review(self) -> str:
        parts: List[str] = [self._negative_sentence()]

        if self.rng.random() < 0.35:
            parts.append(self._neutral_sentence())

        parts.append(self._negative_sentence())

        # ~30% of negative reviews concede something positive.
        if self.rng.random() < 0.30:
            praise = self._fill(self.rng.choice(MILD_PRAISE_TEMPLATES))
            connective = self.rng.choice(CONTRAST_CONNECTIVES)
            parts.append(f"{praise} {connective} {self._negative_sentence()}")

        if self.rng.random() < 0.55:
            parts.append(self.rng.choice(CLOSERS_NEGATIVE))

        return self._join(parts)

    def _join(self, parts: Sequence[str]) -> str:
        text = ". ".join(p.strip() for p in parts if p.strip())
        return text[0].upper() + text[1:] + "."

    # -- public -------------------------------------------------------------

    def generate(
        self,
        size: int = DEFAULT_SIZE,
        positive_ratio: float = POSITIVE_RATIO,
    ) -> Tuple[List[str], List[int]]:
        """Return (texts, labels) with 1 = positive, 0 = negative."""
        n_pos = int(size * positive_ratio)
        n_neg = size - n_pos

        texts = [self._positive_review() for _ in range(n_pos)]
        labels = [1] * n_pos
        texts += [self._negative_review() for _ in range(n_neg)]
        labels += [0] * n_neg

        # Shuffle together so the split isn't ordered by class.
        paired = list(zip(texts, labels))
        self.rng.shuffle(paired)
        texts, labels = zip(*paired)
        return list(texts), list(labels)


# ---------------------------------------------------------------------------
# Real-dataset loading
# ---------------------------------------------------------------------------

_TEXT_COLUMNS = ("text", "review", "review_body", "reviewtext", "content", "body")
_LABEL_COLUMNS = ("label", "sentiment", "rating", "stars", "score", "overall")


def load_real_dataset(path: str) -> Tuple[List[str], List[int]] | None:
    """Load a labelled CSV if present.

    Accepts either an explicit sentiment column (positive/negative, or 1/0) or
    a star rating, in which case 1-2 -> negative, 4-5 -> positive and 3 is
    dropped as genuinely ambiguous. Returns None when the file is unusable so
    the caller can fall back to the generator.
    """
    if not path or not os.path.exists(path):
        return None

    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                logger.warning("Dataset %s has no header row", path)
                return None

            lowered = {name.lower().strip(): name for name in reader.fieldnames}
            text_col = next((lowered[c] for c in _TEXT_COLUMNS if c in lowered), None)
            label_col = next((lowered[c] for c in _LABEL_COLUMNS if c in lowered), None)

            if text_col is None or label_col is None:
                logger.warning(
                    "Dataset %s needs a text column (%s) and a label column (%s); found %s",
                    path, "/".join(_TEXT_COLUMNS), "/".join(_LABEL_COLUMNS),
                    reader.fieldnames,
                )
                return None

            texts: List[str] = []
            labels: List[int] = []
            skipped = 0
            for row in reader:
                text = (row.get(text_col) or "").strip()
                label = _coerce_label(row.get(label_col))
                if not text or label is None:
                    skipped += 1
                    continue
                texts.append(text)
                labels.append(label)

        if len(texts) < 50:
            logger.warning(
                "Dataset %s yielded only %d usable rows — falling back to the "
                "generated corpus", path, len(texts),
            )
            return None

        pos = sum(labels)
        logger.info(
            "Loaded real dataset %s: %d rows (%d positive / %d negative, %d skipped)",
            path, len(texts), pos, len(texts) - pos, skipped,
        )
        return texts, labels

    except Exception:
        logger.exception("Failed to read dataset %s", path)
        return None


def _coerce_label(raw) -> int | None:
    """Map a label cell to 1 (positive), 0 (negative), or None (drop)."""
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if not value:
        return None
    if value in ("positive", "pos", "good", "1", "true", "yes"):
        return 1
    if value in ("negative", "neg", "bad", "0", "false", "no"):
        return 0
    try:
        rating = float(value)
    except ValueError:
        return None
    if rating >= 4:
        return 1
    if rating <= 2:
        return 0
    return None  # 3 stars: genuinely ambiguous, dropped rather than guessed


# ---------------------------------------------------------------------------
# Entry point used by the model
# ---------------------------------------------------------------------------

def load_training_data(
    size: int = DEFAULT_SIZE,
) -> Tuple[List[str], List[int], str]:
    """Return (texts, labels, source_description).

    Prefers a real dataset; falls back to the generated corpus so the service
    always boots. The source string is surfaced through /nlp/metrics so it is
    always obvious which data the live model was trained on.
    """
    path = os.environ.get("DATASET_PATH", DEFAULT_CSV)
    real = load_real_dataset(path)
    if real is not None:
        texts, labels = real
        return texts, labels, f"real dataset ({os.path.basename(path)}, {len(texts)} rows)"

    generator = ReviewCorpusGenerator(seed=RANDOM_SEED)
    texts, labels = generator.generate(size=size)
    return (
        texts,
        labels,
        f"generated corpus ({len(texts)} reviews, seed={RANDOM_SEED}, "
        f"{int(POSITIVE_RATIO * 100)}/{100 - int(POSITIVE_RATIO * 100)} split)",
    )


__all__ = [
    "ReviewCorpusGenerator",
    "load_training_data",
    "load_real_dataset",
    "ASPECTS",
    "DEFAULT_SIZE",
]
