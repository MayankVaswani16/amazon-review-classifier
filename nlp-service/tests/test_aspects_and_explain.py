"""
Tests for aspect extraction and model explainability.

``_extract`` used to be the least-tested and most bug-prone code in the project:
it ignored negation entirely, dropped comparatives, split compound nouns, and
returned results in non-deterministic order. All four are covered here.
"""

import numpy as np
import pytest
import spacy

from aspects import AspectExtractor
from explain import LinearExplainer
from lexicon import LexiconSentiment


@pytest.fixture(scope="module")
def nlp():
    return spacy.load("en_core_web_sm")


@pytest.fixture(scope="module")
def extractor():
    return AspectExtractor(LexiconSentiment())


def analyse(nlp, extractor, text):
    return extractor.analyze(nlp(text))


# ---------------------------------------------------------------------------
# Extraction patterns
# ---------------------------------------------------------------------------

def test_attributive_adjective(nlp, extractor):
    """"the terrible battery" — adjective attaches to the noun via amod."""
    result = analyse(nlp, extractor, "I hate the terrible battery")
    pairs = {(o.aspect.lower(), o.opinion.lower()) for o in result.opinions}
    assert ("battery", "terrible") in pairs


def test_predicative_adjective(nlp, extractor):
    """"the battery is terrible" — both attach to the copula, not each other."""
    result = analyse(nlp, extractor, "The battery is terrible")
    pairs = {(o.aspect.lower(), o.opinion.lower()) for o in result.opinions}
    assert ("battery", "terrible") in pairs


def test_compound_noun_is_kept_whole(nlp, extractor):
    """"battery life" is one aspect, not "battery" plus an unrelated "life"."""
    result = analyse(nlp, extractor, "The battery life is terrible")
    aspects = {o.aspect.lower() for o in result.opinions}
    assert "battery life" in aspects


# ---------------------------------------------------------------------------
# Negation — the original correctness bug
# ---------------------------------------------------------------------------

def test_negated_opinion_is_flagged_and_flipped(nlp, extractor):
    """Regression: "the battery is not terrible" reported battery -> terrible
    as a complaint, because the neg dependency was never checked."""
    result = analyse(nlp, extractor, "The battery is not terrible")
    assert result.opinions, "expected at least one aspect opinion"
    opinion = next(o for o in result.opinions if o.aspect.lower() == "battery")
    assert opinion.negated is True
    assert opinion.polarity > 0
    assert opinion.label == "positive"


def test_unnegated_equivalent_stays_negative(nlp, extractor):
    result = analyse(nlp, extractor, "The battery is terrible")
    opinion = next(o for o in result.opinions if o.aspect.lower() == "battery")
    assert opinion.negated is False
    assert opinion.polarity < 0
    assert opinion.label == "negative"


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_conflicting_aspects_flagged_as_mixed(nlp, extractor):
    result = analyse(
        nlp, extractor,
        "The battery is terrible but the screen is gorgeous",
    )
    assert result.conflict_score > 0.5
    assert result.is_mixed is True


def test_agreeing_aspects_are_not_mixed(nlp, extractor):
    result = analyse(nlp, extractor, "The battery is great and the screen is excellent")
    assert result.is_mixed is False


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_output_order_is_deterministic(nlp, extractor):
    """Regression: nouns/adjectives were built with ``list({...})`` over a set,
    whose iteration order varies with hash randomisation between processes."""
    text = "The battery screen camera and speaker are all excellent quality"
    runs = [tuple(analyse(nlp, extractor, text).nouns) for _ in range(10)]
    assert len(set(runs)) == 1


def test_duplicates_are_removed_preserving_order(nlp, extractor):
    result = analyse(nlp, extractor, "The battery is good. The battery is fine.")
    assert len(result.nouns) == len(set(result.nouns))


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

class _FakeLinear:
    """Minimal stand-in for a fitted LogisticRegression."""
    def __init__(self, coef, intercept):
        self.coef_ = np.array([coef])
        self.intercept_ = np.array([intercept])


@pytest.fixture(scope="module")
def explainer():
    from sklearn.feature_extraction.text import TfidfVectorizer

    corpus = [
        "excellent product great quality",
        "terrible product awful quality",
        "good value nice design",
        "bad value poor design",
    ]
    vec = TfidfVectorizer(ngram_range=(1, 1))
    X = vec.fit_transform(corpus)

    rng = np.random.RandomState(0)
    coef = rng.uniform(-2, 2, size=X.shape[1])
    return LinearExplainer(vec, _FakeLinear(coef, 0.25))


def test_contributions_sum_exactly_to_the_logit(explainer):
    """The defining property of linear attribution.

    Unlike LIME or KernelSHAP these are not approximations — they reconstruct
    the decision exactly, and the test asserts that identity to floating-point
    tolerance.
    """
    text = "excellent product great quality"
    exp = explainer.attribute(text, top_k=100)
    total = sum(c.contribution for c in exp.contributions) + exp.intercept
    assert total == pytest.approx(exp.logit, abs=1e-9)


def test_coverage_reflects_known_vocabulary(explainer):
    known = explainer.attribute("excellent product", top_k=5)
    unknown = explainer.attribute("zorblax frobnicator", top_k=5)
    assert known.coverage == pytest.approx(1.0)
    assert unknown.coverage == pytest.approx(0.0)


def test_counterfactual_actually_flips_the_prediction(explainer):
    """A counterfactual that does not flip the label is not a counterfactual."""
    text = "excellent product great quality terrible awful"
    cf = explainer.counterfactual(text)
    if cf.found:
        assert cf.flipped_label != cf.original_label
        assert cf.removed_terms
        # Every removed term must genuinely be gone from the edited text.
        remaining = cf.edited_text.split()
        assert all(term not in remaining for term in cf.removed_terms)


def test_counterfactual_respects_its_budget(explainer):
    cf = explainer.counterfactual("excellent great good nice value design", max_terms=2)
    assert len(cf.removed_terms) <= 2
