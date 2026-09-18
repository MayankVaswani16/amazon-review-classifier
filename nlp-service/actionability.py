"""
Aspect Actionability Matrix.

WHY THIS EXISTS
---------------
Every sentiment dashboard shows the same two things: a positive/negative split,
and the most frequently mentioned words. Neither answers the question a seller
actually has, which is *"what should I fix first?"*

Frequency alone is misleading. "Product" is the most-mentioned noun in almost
every corpus and is never actionable. And an aspect can be mentioned constantly
while being uncontroversial — "colour" might appear in 40% of reviews and never
be the reason anyone is unhappy.

What matters is whether mentioning an aspect **predicts** a bad review. That is
a lift measurement, borrowed from association-rule mining:

    lift(a) = P(review is negative | aspect a mentioned) - P(review is negative)

An aspect with a high positive lift is one whose presence shifts the odds of an
unhappy customer. Combine that with how often it comes up and how harsh the
language is, and you get a ranking that is genuinely a work queue:

    impact(a) = volume(a) x severity(a) x max(lift(a), 0)

where volume is log-damped so a single overwhelming aspect can't monopolise the
ranking, and severity is the mean negative aspect polarity from the ABSA layer.

The output is a prioritised list: *fix the zipper before you touch the packaging,
because the zipper is mentioned in 300 reviews, is described in strongly negative
terms, and reviews that mention it are 34 points more likely to be negative than
the corpus baseline.* That is a different class of output from "here are your
top ten nouns".
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from aspects import AspectAnalysis

#: Aspects seen fewer times than this are statistically meaningless — a single
#: angry review would otherwise top the chart with a lift of 1.0.
MIN_MENTIONS = 3

#: Volume is log-damped: going from 10 to 100 mentions should matter, but not
#: 10x as much as going from 1 to 10.
def _volume_weight(mentions: int) -> float:
    return math.log1p(mentions)


@dataclass
class AspectStats:
    """Accumulated evidence about one product aspect."""
    aspect: str
    mentions: int = 0
    negative_mentions: int = 0
    positive_mentions: int = 0
    polarity_sum: float = 0.0
    negative_polarity_sum: float = 0.0
    reviews_negative: int = 0          # reviews mentioning it that were negative overall
    examples: List[str] = field(default_factory=list)

    @property
    def mean_polarity(self) -> float:
        return self.polarity_sum / self.mentions if self.mentions else 0.0

    @property
    def severity(self) -> float:
        """Mean magnitude of the negative opinions, in [0, 1]."""
        if not self.negative_mentions:
            return 0.0
        return abs(self.negative_polarity_sum) / self.negative_mentions

    def negative_rate(self, total_reviews_mentioning: int) -> float:
        if not total_reviews_mentioning:
            return 0.0
        return self.reviews_negative / total_reviews_mentioning


class ActionabilityAnalyzer:
    """Builds the actionability ranking from per-review aspect analyses."""

    #: Generic heads that are never a useful work item.
    IGNORED = frozenset({
        "product", "item", "thing", "things", "purchase", "order", "amazon",
        "review", "reviews", "star", "stars", "everything", "anything",
        "nothing", "something", "one", "ones", "lot", "time", "times",
        "day", "days", "week", "weeks", "month", "months", "year", "years",
        "money", "seller", "company", "brand",
    })

    def analyze(
        self,
        analyses: Sequence[AspectAnalysis],
        labels: Sequence[str],
        top_k: int = 10,
        texts: Sequence[str] | None = None,
    ) -> Dict[str, object]:
        """Rank aspects by how much they predict an unhappy customer.

        Parameters
        ----------
        analyses:
            Per-review ABSA output.
        labels:
            Per-review overall verdict ("positive" / "negative" / "mixed").
        texts:
            Optional raw review text, used to attach short quotes as evidence.
        """
        if not analyses:
            return {"baselineNegativeRate": 0.0, "reviewsAnalysed": 0, "aspects": []}

        total_reviews = len(analyses)
        negative_reviews = sum(1 for l in labels if l == "negative")
        baseline = negative_reviews / total_reviews if total_reviews else 0.0

        stats: Dict[str, AspectStats] = {}
        reviews_mentioning: Dict[str, int] = defaultdict(int)

        for i, analysis in enumerate(analyses):
            label = labels[i] if i < len(labels) else "positive"
            seen_this_review = set()

            for opinion in analysis.opinions:
                key = self._normalise(opinion.aspect)
                if not key or key in self.IGNORED:
                    continue

                st = stats.setdefault(key, AspectStats(aspect=key))
                st.mentions += 1
                st.polarity_sum += opinion.polarity

                if opinion.label == "negative":
                    st.negative_mentions += 1
                    st.negative_polarity_sum += opinion.polarity
                    if texts is not None and len(st.examples) < 3:
                        quote = self._quote(opinion.sentence or texts[i])
                        if quote and quote not in st.examples:
                            st.examples.append(quote)
                elif opinion.label == "positive":
                    st.positive_mentions += 1

                # Count each aspect at most once per review for the rate,
                # otherwise a review repeating "battery" five times skews it.
                if key not in seen_this_review:
                    seen_this_review.add(key)
                    reviews_mentioning[key] += 1
                    if label == "negative":
                        st.reviews_negative += 1

        rows: List[Dict[str, object]] = []
        for key, st in stats.items():
            if st.mentions < MIN_MENTIONS:
                continue
            mentioning = reviews_mentioning[key]
            rate = st.negative_rate(mentioning)
            lift = rate - baseline
            impact = _volume_weight(st.mentions) * st.severity * max(lift, 0.0)

            rows.append({
                "aspect": key,
                "mentions": st.mentions,
                "negativeMentions": st.negative_mentions,
                "positiveMentions": st.positive_mentions,
                "meanPolarity": round(st.mean_polarity, 4),
                "negativeRate": round(rate, 4),
                "lift": round(lift, 4),
                "impactScore": round(impact, 4),
                "examples": st.examples,
            })

        rows.sort(key=lambda r: r["impactScore"], reverse=True)

        return {
            "baselineNegativeRate": round(baseline, 4),
            "reviewsAnalysed": total_reviews,
            "aspects": rows[:top_k],
        }

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _normalise(aspect: str) -> str:
        """Lowercase, strip punctuation, and collapse trivial plurals."""
        text = re.sub(r"[^a-z\s]", "", aspect.lower()).strip()
        if not text:
            return ""
        # Only depluralise the head word, and only for regular plurals —
        # "glass" and "lens" must not become "glas"/"len".
        words = text.split()
        head = words[-1]
        if len(head) > 3 and head.endswith("s") and not head.endswith(("ss", "us", "is")):
            words[-1] = head[:-1]
        return " ".join(words)

    @staticmethod
    def _quote(sentence: str, limit: int = 120) -> str:
        s = " ".join(sentence.split())
        return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


__all__ = ["ActionabilityAnalyzer", "AspectStats", "MIN_MENTIONS"]
