"""
Out-of-distribution reality check.

WHY THIS EXISTS
---------------
A held-out split of the training corpus measures the wrong thing. When the
training data comes from a generator, the test split comes from the *same*
generator — same templates, same vocabulary, same sentence shapes — so the
model scores ~99% by memorising the grammar rather than learning sentiment.
That number is real arithmetic on fake data, and quoting it as "accuracy"
would be dishonest.

This module holds a small corpus written by hand, deliberately **unlike** the
generated training data, containing the constructions that actually break
sentiment classifiers in production:

* negation, including double negation and negated praise
* mixed sentiment where the verdict hinges on a contrastive conjunction
* implicit sentiment with no polar adjective at all
  ("returned it the same day", "it lasted three days")
* sarcasm and idiom
* comparative framing ("better than the last one I bought")
* out-of-vocabulary and misspelled words
* neutral/factual statements that should not be forced into a polarity

The gap between in-distribution and out-of-distribution accuracy is the single
most informative number this project produces. Reporting only the first would
be the same mistake the original pipeline made.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

#: (text, expected_label). "neutral" means the correct behaviour is *not* to
#: assert a strong polarity; scoring treats it separately from pos/neg.
BENCHMARK: Sequence[Tuple[str, str]] = (
    # --- straightforward, but not in the training templates ---------------
    ("Bought this for my daughter and she uses it every single day. Money well spent.", "positive"),
    ("Honestly one of the better purchases I've made this year.", "positive"),
    ("Arrived quickly, packaged nicely, does exactly what it says.", "positive"),
    ("Third one I've ordered. Says it all really.", "positive"),
    ("I've had zero problems with it in six months of daily use.", "positive"),
    ("It broke. Two weeks. That's it.", "negative"),
    ("Sent it back the same day it arrived.", "negative"),
    ("Lasted about three days before it stopped charging.", "negative"),
    ("Save yourself the hassle and buy a different brand.", "negative"),
    ("I want my money back and the seller won't respond.", "negative"),

    # --- negation ---------------------------------------------------------
    ("This is not a good product.", "negative"),
    ("It isn't great, honestly.", "negative"),
    ("Not worth the money at all.", "negative"),
    ("I wouldn't recommend this to anyone.", "negative"),
    ("It's not bad for the price.", "positive"),
    ("Nothing wrong with it at all.", "positive"),
    ("I can't fault it.", "positive"),
    ("No complaints whatsoever.", "positive"),
    ("Not the best I've owned but certainly not the worst.", "neutral"),
    ("I never had a single issue with it.", "positive"),

    # --- mixed sentiment: the verdict hinges on the contrast --------------
    ("The screen is gorgeous but the battery is completely useless.", "negative"),
    ("Battery life is poor, however everything else about it is excellent.", "positive"),
    ("Great product, terrible packaging.", "positive"),
    ("Beautiful design, shame it stopped working after a month.", "negative"),
    ("It's slow to start up, but once running it's brilliant.", "positive"),
    ("Love the look of it. Hate using it.", "negative"),
    ("Cheap materials, but for this price I honestly can't complain.", "positive"),
    ("Works perfectly. Arrived two weeks late and support was useless.", "negative"),

    # --- implicit sentiment, no polar adjective ---------------------------
    ("Returned it.", "negative"),
    ("It does what it's supposed to do.", "positive"),
    ("I'm buying another one for my office.", "positive"),
    ("Went straight in the bin.", "negative"),
    ("My wife has already asked me to order her one.", "positive"),
    ("The charging port gave up after a fortnight.", "negative"),
    ("Still going strong two years later.", "positive"),
    ("Had to buy a replacement within a month.", "negative"),

    # --- sarcasm and idiom ------------------------------------------------
    ("Great, another product that stops working after the return window closes.", "negative"),
    ("Fantastic if you enjoy reading instruction manuals for two hours.", "negative"),
    ("Well, that was forty pounds I'll never see again.", "negative"),
    ("Does the job.", "positive"),
    ("It's a steal at this price.", "positive"),
    ("Absolute rip off.", "negative"),

    # --- comparative framing ----------------------------------------------
    ("Much better than the one I bought last year.", "positive"),
    ("Worse than the cheaper version I replaced.", "negative"),
    ("Not as good as the reviews suggested.", "negative"),
    ("Better than expected for something this cheap.", "positive"),

    # --- out-of-vocabulary / misspelling ----------------------------------
    ("The zorpal mechanism is fantastic and the flurbing works great.", "positive"),
    ("Absolutley terrbile qualty, verry dissapointed.", "negative"),
    ("Excelent product, arived on time, wuld buy agian.", "positive"),
    ("The whatchamacallit snapped off immediately.", "negative"),

    # --- neutral / factual: should NOT be a confident polarity ------------
    ("It is blue and made of plastic.", "neutral"),
    ("Arrived Tuesday.", "neutral"),
    ("This is the 500ml size, not the 750ml.", "neutral"),
    ("I ordered two of these.", "neutral"),
    ("Comes with a charger and a manual.", "neutral"),

    # --- intensity ---------------------------------------------------------
    ("Slightly disappointed with the finish.", "negative"),
    ("Absolutely thrilled with this purchase!", "positive"),
    ("Mildly annoying but nothing serious.", "negative"),
    ("Incredibly well built for the money.", "positive"),

    # --- longer, realistic reviews ----------------------------------------
    (
        "I was sceptical given some of the reviews here but I'm glad I took the "
        "chance. Setup took about ten minutes, the instructions were clear enough, "
        "and it's been running without a hitch for three weeks now. The only thing "
        "I'd change is the length of the cable.",
        "positive",
    ),
    (
        "Ordered this on the strength of the photos. What turned up was noticeably "
        "smaller and the finish is nothing like the listing. Customer service offered "
        "me a partial refund which I declined on principle. Avoid.",
        "negative",
    ),
    (
        "Does what it needs to. Nothing exceptional, nothing terrible. If you need "
        "one of these and don't want to spend a fortune it'll be fine.",
        "neutral",
    ),
    (
        "Second time buying this. First one lasted four years of daily abuse before "
        "the motor finally gave out, which I think is pretty reasonable. No hesitation "
        "buying again.",
        "positive",
    ),
    (
        "The listing says waterproof. It is not waterproof. Mine died the first time "
        "it got caught in the rain and the seller is now claiming misuse. Genuinely "
        "the worst experience I've had on this site.",
        "negative",
    ),
)


def split_benchmark() -> Tuple[List[str], List[str]]:
    """Return (texts, labels) for the whole benchmark."""
    return [t for t, _ in BENCHMARK], [l for _, l in BENCHMARK]


def score_predictions(
    expected: Sequence[str],
    predicted: Sequence[str],
) -> Dict[str, object]:
    """Score predictions against the benchmark.

    Polar cases (positive/negative) are scored strictly. Neutral cases are
    scored leniently: any answer is acceptable *provided* the engine flagged
    it as uncertain or mixed, because a neutral review genuinely has no right
    polar answer — what matters is that the system doesn't assert one
    confidently.
    """
    polar_total = polar_correct = 0
    neutral_total = neutral_ok = 0
    errors: List[Dict[str, str]] = []

    for exp, pred in zip(expected, predicted):
        if exp == "neutral":
            neutral_total += 1
            if pred in ("neutral", "mixed", "uncertain"):
                neutral_ok += 1
        else:
            polar_total += 1
            # "mixed" is an acceptable hedge on a genuinely mixed review but
            # counts as a miss when a clear polarity was expected.
            if pred == exp:
                polar_correct += 1
            else:
                errors.append({"expected": exp, "predicted": pred})

    return {
        "polarTotal": polar_total,
        "polarCorrect": polar_correct,
        "polarAccuracy": polar_correct / polar_total if polar_total else 0.0,
        "neutralTotal": neutral_total,
        "neutralHandled": neutral_ok,
        "errors": errors,
    }


__all__ = ["BENCHMARK", "split_benchmark", "score_predictions"]
