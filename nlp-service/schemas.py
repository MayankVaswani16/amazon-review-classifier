"""Pydantic schemas for the NLP microservice.

Field names are **camelCase** on purpose. They are consumed directly by a Java
DTO layer via Jackson, which binds by property name; matching the Java
convention here means neither side needs a naming strategy or per-field
annotations. It is unidiomatic Python and a deliberate cross-language
integration decision.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000,
                      description="Review text to analyse")


class BulkPredictRequest(BaseModel):
    reviews: List[str] = Field(..., min_length=1, max_length=1000,
                               description="Batch of review texts")


class ExplainRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    topK: int = Field(default=12, ge=1, le=50)


class ActionabilityRequest(BaseModel):
    """A corpus of reviews to rank aspects across."""
    reviews: List[str] = Field(..., min_length=1, max_length=5000)
    topK: int = Field(default=10, ge=1, le=50)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class AspectOpinionSchema(BaseModel):
    aspect: str
    opinion: str
    polarity: float
    label: str
    negated: bool
    relation: str
    sentence: str = ""


class TokenContributionSchema(BaseModel):
    term: str
    weight: float
    value: float
    contribution: float
    direction: str


class CounterfactualSchema(BaseModel):
    found: bool
    removedTerms: List[str] = Field(default_factory=list)
    originalLabel: str = ""
    flippedLabel: str = ""
    originalConfidence: float = 0.0
    flippedConfidence: float = 0.0
    editedText: str = ""


class PredictResponse(BaseModel):
    """One review's analysis.

    The first six fields preserve the original wire format so existing
    consumers keep working; everything after is additive.
    """
    label: str = Field(..., description="positive | negative | mixed")
    confidence: float = Field(..., ge=0.0, le=1.0)
    nouns: List[str] = Field(default_factory=list)
    adjectives: List[str] = Field(default_factory=list)
    featureSentimentPairs: List[List[str]] = Field(default_factory=list)
    processedText: str = ""

    # -- aspect-level ------------------------------------------------------
    aspects: List[AspectOpinionSchema] = Field(default_factory=list)
    conflictScore: float = 0.0
    isMixed: bool = False

    # -- engine transparency ----------------------------------------------
    modelLabel: str = ""
    modelConfidence: float = 0.0
    lexiconLabel: str = ""
    lexiconScore: float = 0.0
    coverage: float = Field(default=0.0, description="Share of tokens the model knows")
    lowSignal: bool = Field(default=False, description="Neither engine had evidence")
    uncertain: bool = False
    agreement: bool = True


class BulkPredictResponse(BaseModel):
    results: List[PredictResponse]


class ExplainResponse(BaseModel):
    logit: float = 0.0
    intercept: float = 0.0
    contributions: List[TokenContributionSchema] = Field(default_factory=list)
    counterfactual: Optional[CounterfactualSchema] = None
    coverage: float = 0.0
    knownTerms: int = 0
    totalTerms: int = 0
    lexicon: dict = Field(default_factory=dict)


class AspectImpact(BaseModel):
    """One row of the Aspect Actionability Matrix."""
    aspect: str
    mentions: int
    negativeMentions: int
    positiveMentions: int
    meanPolarity: float
    negativeRate: float
    lift: float = Field(
        ..., description="negativeRate minus the corpus-wide negative rate",
    )
    impactScore: float = Field(
        ..., description="Prioritisation score: volume x severity x lift",
    )
    examples: List[str] = Field(default_factory=list)


class ActionabilityResponse(BaseModel):
    baselineNegativeRate: float
    reviewsAnalysed: int
    aspects: List[AspectImpact] = Field(default_factory=list)


class SmoteDistribution(BaseModel):
    before: dict = Field(default_factory=dict)
    after: dict = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    """Honest model evaluation.

    ``inDistribution`` is measured on a held-out split of the training corpus.
    When that corpus is generated, this number reflects how well the model
    memorised the generator and should not be quoted as accuracy.
    ``outOfDistribution`` is the realistic estimate.
    """
    modelVersion: str = ""
    trainedOn: str = ""
    trainingSamples: int = 0
    testSamples: int = 0
    vocabularySize: int = 0
    accuracy: float = 0.0
    macroF1: float = 0.0
    weightedF1: float = 0.0
    rocAuc: float = 0.0
    crossValF1Mean: float = 0.0
    crossValF1Std: float = 0.0
    perClass: dict = Field(default_factory=dict)
    confusionMatrix: dict = Field(default_factory=dict)
    outOfDistribution: dict = Field(default_factory=dict)


class TopFeaturesResponse(BaseModel):
    positive: List[dict] = Field(default_factory=list)
    negative: List[dict] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool = False
    vectorizer_loaded: bool = False
    modelVersion: str = ""
    ready: bool = False
