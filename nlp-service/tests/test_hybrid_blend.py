"""
Tests for the hybrid blend and the API surface.

The blend is where the two engines are combined, and it is the piece whose
behaviour was changed on the basis of measurement rather than intuition. These
tests pin the properties that measurement established.
"""

import pytest

from model import (
    LOW_COVERAGE_THRESHOLD,
    MAX_BLEND_WEIGHT,
    MIN_BLEND_WEIGHT,
    SentimentModel,
    TextPreprocessor,
)


@pytest.fixture(scope="module")
def model():
    """A trained model. Loads the cached artefact when available."""
    m = SentimentModel(TextPreprocessor())
    if not m.load():
        m.train()
    return m


# ---------------------------------------------------------------------------
# Abstention: the bug that made the hybrid worse than the model alone
# ---------------------------------------------------------------------------

def test_lexicon_abstention_does_not_drag_the_verdict(model):
    """A lexicon score of 0.0 means "no opinion", not "neutral opinion".

    Averaging an abstention in as p(positive)=0.5 pulled confident, correct
    model predictions toward the middle. Measured on the out-of-distribution
    benchmark this cost ~9 points of accuracy and made the hybrid *worse* than
    the classifier alone. With the fix, an abstaining lexicon contributes
    nothing and the model's verdict survives intact.
    """
    model_proba = 0.95  # model is confident this is positive

    # Abstaining: the model's verdict and confidence pass through untouched.
    # Under the old blend this was averaged with p=0.5 and diluted.
    label, confidence, _ = model._blend(model_proba, 0.0, False, 1.0)
    assert label == "positive"
    assert confidence == pytest.approx(model_proba, abs=1e-6)

    # A lexicon with a genuine opposing opinion *should* move the result —
    # abstention and disagreement must not be treated the same way.
    _, opposed_confidence, _ = model._blend(model_proba, -0.6, True, 1.0)
    assert opposed_confidence < confidence

    # A lexicon that agrees keeps the label and stays well clear of the
    # disagreeing case. It does not *raise* confidence above the model's: linear
    # opinion pooling is bounded by its most confident component, so blending in
    # a less-certain second opinion is always conservative. That is the intended
    # trade-off — the blend buys robustness on unfamiliar text, not sharper
    # confidence on text the model already handles well.
    agreeing_label, agreeing_confidence, _ = model._blend(model_proba, 0.6, True, 1.0)
    assert agreeing_label == "positive"
    assert agreeing_confidence > opposed_confidence


def test_both_engines_silent_is_reported_as_low_signal(model):
    label, confidence, low_signal = model._blend(0.9, 0.0, False, 0.0)
    assert low_signal is True
    assert confidence == pytest.approx(0.5)


def test_low_coverage_shifts_weight_to_the_lexicon(model):
    """When the model recognises almost nothing, the lexicon should decide."""
    # Model says positive, lexicon says clearly negative, model knows nothing.
    label, _, _ = model._blend(0.95, -0.8, True, 0.0)
    assert label == "negative"


def test_full_coverage_lets_the_model_participate(model):
    """With full coverage and a weak lexicon signal, the model is not ignored."""
    label, _, _ = model._blend(0.99, -0.05, True, 1.0)
    assert label == "positive"


def test_blend_weight_stays_within_bounds(model):
    assert MIN_BLEND_WEIGHT <= model.blend_weight <= MAX_BLEND_WEIGHT


def test_confidence_is_always_a_probability(model):
    for proba in (0.0, 0.25, 0.5, 0.75, 1.0):
        for lex_score in (-1.0, -0.3, 0.0, 0.3, 1.0):
            for coverage in (0.0, 0.5, 1.0):
                _, confidence, _ = model._blend(proba, lex_score, lex_score != 0.0, coverage)
                assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# End-to-end prediction behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("This is absolutely excellent, works perfectly", "positive"),
    ("Complete waste of money, broke immediately", "negative"),
    ("This product is not good at all", "negative"),
])
def test_clear_cases_are_classified_correctly(model, text, expected):
    assert model.predict(text).label == expected


def test_out_of_vocabulary_input_is_flagged_not_guessed(model):
    """The original pipeline's most dangerous failure.

    Unseen vocabulary produced an all-zero TF-IDF row, so the prediction
    collapsed to the model's intercept — a confident-looking verdict derived
    from no evidence. It must now be flagged instead.
    """
    result = model.predict("zorblax frobnicator quux blivet")
    assert result.low_signal is True
    assert result.coverage < LOW_COVERAGE_THRESHOLD


def test_batch_matches_single_prediction(model):
    """Vectorised batch inference must not change the answer."""
    texts = [
        "This is excellent and works perfectly",
        "Terrible product, complete waste of money",
        "The battery is not terrible",
    ]
    singles = [model.predict(t) for t in texts]
    batched = model.predict_batch(texts)

    for single, batch in zip(singles, batched):
        assert single.label == batch.label
        assert single.confidence == pytest.approx(batch.confidence, abs=1e-9)
        assert single.processed_text == batch.processed_text


def test_negation_survives_preprocessing(model):
    """NLTK's stopword list contains "not". Removing it turns "not good" into
    "good" and silently inverts the label."""
    processed = model.preprocessor.preprocess("this product is not good")
    assert "not" in processed.split()


def test_explanation_is_available_and_consistent(model):
    payload = model.explain("Complete waste of money, terrible quality")
    assert payload
    assert payload["contributions"]
    reconstructed = sum(c["contribution"] for c in payload["contributions"])
    # Only the top-k terms are returned, so the sum is a lower bound on the
    # magnitude rather than an exact match — but the sign must agree.
    assert reconstructed < 0


# ---------------------------------------------------------------------------
# Metrics honesty
# ---------------------------------------------------------------------------

def test_metrics_include_the_unflattering_number(model):
    """The out-of-distribution score must be published, not just accuracy."""
    if not model.metrics:
        pytest.skip("model has no cached metrics")
    ood = model.metrics.get("outOfDistribution")
    assert ood, "out-of-distribution benchmark missing from metrics"
    assert "modelAccuracy" in ood
    assert "lexiconAccuracy" in ood
    assert 0.0 <= ood["modelAccuracy"] <= 1.0
