"""
FastAPI NLP Microservice for Amazon Review Sentiment Classification.

Endpoints:
  POST /nlp/predict       — single review prediction
  POST /nlp/predict/bulk  — batch predictions
  GET  /nlp/health        — health check
  GET  /nlp/tsne/before   — t-SNE before SMOTE (PNG)
  GET  /nlp/tsne/after    — t-SNE after SMOTE (PNG)
  GET  /nlp/smote-stats   — SMOTE class distributions
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from schemas import (
    PredictRequest,
    BulkPredictRequest,
    PredictResponse,
    BulkPredictResponse,
    HealthResponse,
    SmoteDistribution,
)
from model import TextPreprocessor, SentimentModel, NLPAnalyzer, STATIC_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global singletons
preprocessor = TextPreprocessor()
sentiment_model = SentimentModel(preprocessor)
nlp_analyzer = NLPAnalyzer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load or train model on startup."""
    if not sentiment_model.load():
        logger.info("No saved model found. Training on synthetic data …")
        sentiment_model.train()
    yield


app = FastAPI(
    title="Amazon Review NLP Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Predict ───────────────────────────────────────────────────────────────
@app.post("/nlp/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Predict sentiment and extract NLP features for a single review."""
    try:
        label, confidence, processed_text = sentiment_model.predict(request.text)
        analysis = nlp_analyzer.analyze(request.text)
        return PredictResponse(
            label=label,
            confidence=confidence,
            nouns=analysis["nouns"],
            adjectives=analysis["adjectives"],
            featureSentimentPairs=analysis["featureSentimentPairs"],
            processedText=processed_text,
        )
    except Exception as e:
        logger.exception("Prediction error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/nlp/predict/bulk", response_model=BulkPredictResponse)
async def predict_bulk(request: BulkPredictRequest):
    """Predict sentiment for a batch of reviews (optimised)."""
    try:
        predictions = sentiment_model.predict_batch(request.reviews)
        analyses = nlp_analyzer.analyze_batch(request.reviews)
        results = [
            PredictResponse(
                label=label,
                confidence=confidence,
                processedText=processed,
                nouns=analysis["nouns"],
                adjectives=analysis["adjectives"],
                featureSentimentPairs=analysis["featureSentimentPairs"],
            )
            for (label, confidence, processed), analysis
            in zip(predictions, analyses)
        ]
        return BulkPredictResponse(results=results)
    except Exception as e:
        logger.exception("Bulk prediction error")
        raise HTTPException(status_code=500, detail=str(e))


# ── t-SNE images ──────────────────────────────────────────────────────────
@app.get("/nlp/tsne/before")
async def tsne_before():
    path = os.path.join(STATIC_DIR, "tsne_before.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="t-SNE before image not found")
    return FileResponse(path, media_type="image/png")


@app.get("/nlp/tsne/after")
async def tsne_after():
    path = os.path.join(STATIC_DIR, "tsne_after.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="t-SNE after image not found")
    return FileResponse(path, media_type="image/png")


# ── SMOTE stats ───────────────────────────────────────────────────────────
@app.get("/nlp/smote-stats", response_model=SmoteDistribution)
async def smote_stats():
    return SmoteDistribution(
        before=sentiment_model.smote_distribution.get("before", {}),
        after=sentiment_model.smote_distribution.get("after", {}),
    )


# ── Health ────────────────────────────────────────────────────────────────
@app.get("/nlp/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model_loaded=sentiment_model.classifier is not None,
        vectorizer_loaded=sentiment_model.vectorizer is not None,
    )
