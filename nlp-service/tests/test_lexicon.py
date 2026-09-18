"""
Tests for the rule-based sentiment lexicon.

These are the highest-value tests in the project: the lexicon is where negation,
intensification and contrast are actually decided, and every one of those is a
place where a silent regression would flip a verdict without raising anything.
"""

import pytest

from lexicon import (
    NEGATION_SCALAR,
    LexiconSentiment,
)


@pytest.fixture(scope="module")
def lex():
    return LexiconSentiment()


# ---------------------------------------------------------------------------
# Negation — the bug that motivated the whole module
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("this product is good", "positive"),
    ("this product is not good", "negative"),
    ("this product is terrible", "negative"),
    ("this product is not terrible", "positive"),
    ("I would not recommend this", "negative"),
    ("I can't fault it", "positive"),
    ("nothing wrong with it", "positive"),
    ("it isn't great", "negative"),
])
def test_negation_flips_polarity(lex, text, expected):
    assert lex.score(text).label == expected


def test_negation_is_damped_not_mirrored(lex):
    """"not terrible" is milder praise than "excellent" is praise.

    A plain sign flip would make them equal in magnitude, which is wrong: English
    negation weakens rather than mirrors. That is what NEGATION_SCALAR encodes.
    """
    assert NEGATION_SCALAR < 0
    assert abs(NEGATION_SCALAR) < 1.0

    not_terrible = lex.score("the battery is not terrible").compound
    excellent = lex.score("the battery is excellent").compound
    assert 0 < not_terrible < excellent


def test_negation_respects_window(lex):
    """A negator far from the sentiment word must not flip it."""
    near = lex.score("it is not good")
    far = lex.score("it is not the sort of thing I expected but honestly good")
    assert near.label == "negative"
    assert far.label == "positive"


# ---------------------------------------------------------------------------
# Contrastive conjunctions
# ---------------------------------------------------------------------------

def test_contrast_weights_the_second_clause(lex):
    """Identical words, opposite order, opposite verdict.

    "X is terrible but Y is gorgeous" resolves positive; reversed it resolves
    negative. A bag-of-words model cannot distinguish these at all.
    """
    a = lex.score("the battery is terrible but the screen is gorgeous")
    b = lex.score("the screen is gorgeous but the battery is terrible")
    assert a.label == "positive"
    assert b.label == "negative"
    assert a.compound > 0 > b.compound


# ---------------------------------------------------------------------------
# Intensifiers
# ---------------------------------------------------------------------------

def test_amplifier_increases_magnitude(lex):
    plain = abs(lex.score("the finish is disappointing").compound)
    amped = abs(lex.score("the finish is extremely disappointing").compound)
    assert amped > plain


def test_downtoner_reduces_magnitude(lex):
    plain = abs(lex.score("the finish is disappointing").compound)
    damped = abs(lex.score("the finish is slightly disappointing").compound)
    assert damped < plain


# ---------------------------------------------------------------------------
# Abstention — "no opinion" must be distinguishable from "neutral opinion"
# ---------------------------------------------------------------------------

def test_unknown_vocabulary_abstains(lex):
    """This distinction drives the hybrid blend.

    Conflating "found no sentiment words" with "found neutral sentiment" cost
    ~9 points of out-of-distribution accuracy before it was fixed, because a
    zero score was averaged in as p(positive)=0.5 and dragged correct model
    predictions to the middle.
    """
    result = lex.score("the zorblax frobnicator arrived on tuesday")
    assert result.has_signal is False
    assert result.compound == 0.0
    assert result.label == "neutral"


def test_known_vocabulary_has_signal(lex):
    assert lex.score("this is excellent").has_signal is True


def test_empty_input_is_safe(lex):
    for text in ("", "   ", "!!!", "12345"):
        result = lex.score(text)
        assert result.compound == 0.0
        assert result.has_signal is False


# ---------------------------------------------------------------------------
# Aspect nouns must not carry polarity of their own
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("poor quality", "negative"),
    ("cheap quality", "negative"),
    ("excellent build quality", "positive"),
    ("the sound quality is bad", "negative"),
])
def test_aspect_nouns_do_not_skew_polarity(lex, text, expected):
    """Regression: "quality" once carried +1.6, so "cheap quality" scored ~0.

    Polarity belongs to the opinion word; the noun is the target.
    """
    assert lex.score(text).label == expected


@pytest.mark.parametrize("text", ["free returns", "easy return policy"])
def test_ambiguous_words_are_not_naively_negative(lex, text):
    """"return" is negative in "had to return it" and positive in "free returns"."""
    assert lex.score(text).label != "negative"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_scoring_is_deterministic(lex):
    text = "the battery is not great but the screen is gorgeous"
    scores = {lex.score(text).compound for _ in range(20)}
    assert len(scores) == 1


def test_compound_stays_in_range(lex):
    extreme = " ".join(["absolutely terrible awful horrible garbage"] * 50)
    assert -1.0 <= lex.score(extreme).compound <= 1.0
