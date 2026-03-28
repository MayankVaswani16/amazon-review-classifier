"""Pydantic schemas for the NLP microservice."""

from pydantic import BaseModel, Field
from typing import List, Optional


class PredictRequest(BaseModel):
    """Single review prediction request."""
    text: str = Field(..., min_length=1, description="Review text to analyze")


class BulkPredictRequest(BaseModel):
    """Bulk review prediction request."""
    reviews: List[str] = Field(..., min_length=1, description="List of review texts")


class FeatureSentimentPair(BaseModel):
    """A noun-adjective pair extracted via dependency parsing."""
    feature: str
    sentiment: str


class PredictResponse(BaseModel):
    """Prediction result for a single review."""
    label: str = Field(..., description="positive or negative")
    confidence: float = Field(..., ge=0.0, le=1.0)
    nouns: List[str] = Field(default_factory=list)
    adjectives: List[str] = Field(default_factory=list)
    featureSentimentPairs: List[List[str]] = Field(default_factory=list)
    processedText: str = Field(default="")


class BulkPredictResponse(BaseModel):
    """Bulk prediction results."""
    results: List[PredictResponse]


class SmoteDistribution(BaseModel):
    """Class distribution before/after SMOTE."""
    before: dict = Field(default_factory=dict)
    after: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    model_loaded: bool = False
    vectorizer_loaded: bool = False
