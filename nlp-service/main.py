"""
FastAPI NLP microservice for Amazon review sentiment analysis.

Endpoints
---------
POST /nlp/predict          single review: sentiment + aspects + engine detail
POST /nlp/predict/bulk     batched, vectorised
POST /nlp/explain          exact token attribution + counterfactual flip
POST /nlp/actionability    Aspect Actionability Matrix over a review corpus
GET  /nlp/metrics          honest evaluation, in- and out-of-distribution
GET  /nlp/model/features   the terms the model weights most heavily
GET  /nlp/smote-stats      class distribution before/after resampling
GET  /nlp/tsne/{before,after}   diagnostic projections (PNG)
GET  /nlp/health           liveness + readiness

A NOTE ON `def` vs `async def`
------------------------------
Every handler below is a plain ``def``, not ``async def``, and that is
deliberate. FastAPI runs an ``async def`` handler directly on the event loop;
everything these handlers call — spaCy parsing, TF-IDF transform,
``predict_proba`` — is synchronous and CPU-bound. Declaring them ``async``
(as the original did) pins the event loop for the full duration of every
request, serialising all concurrency to zero and starving the health check
during long batches, which can get the container killed mid-job. Declaring them
``def`` makes FastAPI run them in a threadpool instead, leaving the loop free.
spaCy and scikit-learn release the GIL inside their native code, so this is a
real throughput win rather than a cosmetic change.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from actionability import ActionabilityAnalyzer
from model import (
    MODEL_VERSION,
    STATIC_DIR,
    NLPAnalyzer,
    SentimentModel,
    TextPreprocessor,
)
from schemas import (
    ActionabilityRequest,
    ActionabilityResponse,
    BulkPredictRequest,
    BulkPredictResponse,
    ExplainRequest,
    ExplainResponse,
    HealthResponse,
    MetricsResponse,
    PredictRequest,
    PredictResponse,
    SmoteDistribution,
    TopFeaturesResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Module-level singletons. These load ~100MB of spaCy and scikit-learn state;
# constructing them per request would be catastrophic.
preprocessor = TextPreprocessor()
sentiment_model = SentimentModel(preprocessor)
nlp_analyzer = NLPAnalyzer(sentiment_model.lexicon)
actionability = ActionabilityAnalyzer()

#: Flipped once the model is usable. The health check reports it so an
#: orchestrator can distinguish "process is up" from "can actually serve".
_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load a cached model, or train one if none matches this code version."""
    global _ready
    if not sentiment_model.load():
        logger.info("No usable cached model — training (this takes a minute)…")
        sentiment_model.train()
    _ready = True
    logger.info("NLP service ready (model %s)", MODEL_VERSION)
    yield


app = FastAPI(
    title="Amazon Review NLP Service",
    version=MODEL_VERSION,
    lifespan=lifespan,
    description=(
        "Hybrid sentiment engine: calibrated TF-IDF + Logistic Regression "
        "blended with a rule-based valence lexicon, plus dependency-based "
        "aspect extraction, exact linear attribution and counterfactuals."
    ),
)


def _require_ready():
    if not _ready or sentiment_model.classifier is None:
        raise HTTPException(status_code=503, detail="Model is still loading")


def _to_response(result, analysis) -> PredictResponse:
    """Merge the sentiment verdict and the aspect analysis into the wire shape."""
    return PredictResponse(
        label=result.label,
        confidence=result.confidence,
        nouns=analysis.nouns,
        adjectives=analysis.adjectives,
        featureSentimentPairs=analysis.legacy_pairs(),
        processedText=result.processed_text,
        aspects=[o.as_dict() for o in analysis.opinions],
        conflictScore=analysis.conflict_score,
        isMixed=analysis.is_mixed,
        modelLabel=result.model_label,
        modelConfidence=result.model_confidence,
        lexiconLabel=result.lexicon_label,
        lexiconScore=result.lexicon_score,
        coverage=result.coverage,
        lowSignal=result.low_signal,
        uncertain=result.uncertain,
        agreement=result.agreement,
    )


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

@app.post("/nlp/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    """Analyse a single review.

    The classifier runs on preprocessed text; the aspect extractor runs on the
    **raw** text, because dependency parsing needs real grammar and the
    preprocessing pipeline strips exactly the tokens it relies on.
    """
    _require_ready()
    try:
        analysis = nlp_analyzer.analyze(request.text)
        result = sentiment_model.predict(request.text, analysis)
        return _to_response(result, analysis)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Prediction failed")


@app.post("/nlp/predict/bulk", response_model=BulkPredictResponse)
def predict_bulk(request: BulkPredictRequest):
    """Batched prediction — one spaCy pass, one transform, one predict_proba."""
    _require_ready()
    try:
        analyses = nlp_analyzer.analyze_batch(request.reviews)
        results = sentiment_model.predict_batch(request.reviews, analyses)
        return BulkPredictResponse(
            results=[_to_response(r, a) for r, a in zip(results, analyses)]
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Bulk prediction failed")
        raise HTTPException(status_code=500, detail="Bulk prediction failed")


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

@app.post("/nlp/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest):
    """Why did the model decide that?

    Returns per-term contributions that sum exactly to the decision logit, plus
    the minimal set of terms whose removal flips the verdict.
    """
    _require_ready()
    try:
        payload = sentiment_model.explain(request.text, top_k=request.topK)
        if not payload:
            raise HTTPException(status_code=503, detail="Explainer unavailable")
        return ExplainResponse(**payload)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Explanation failed")
        raise HTTPException(status_code=500, detail="Explanation failed")


@app.post("/nlp/actionability", response_model=ActionabilityResponse)
def rank_actionability(request: ActionabilityRequest):
    """Rank product aspects by how strongly they predict an unhappy customer.

    This is the "what should I fix first" view: volume x severity x lift over
    the corpus baseline, rather than a raw frequency count.
    """
    _require_ready()
    try:
        analyses = nlp_analyzer.analyze_batch(request.reviews)
        results = sentiment_model.predict_batch(request.reviews, analyses)
        payload = actionability.analyze(
            analyses,
            [r.label for r in results],
            top_k=request.topK,
            texts=request.reviews,
        )
        return ActionabilityResponse(**payload)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Actionability analysis failed")
        raise HTTPException(status_code=500, detail="Actionability analysis failed")


# ---------------------------------------------------------------------------
# Model introspection
# ---------------------------------------------------------------------------

@app.get("/nlp/metrics", response_model=MetricsResponse)
def metrics():
    """Model evaluation.

    ``outOfDistribution`` is the number that matters. The top-level accuracy is
    measured on a held-out split of the training corpus; when that corpus is
    generated, it mostly reflects how well the model memorised the generator.
    """
    _require_ready()
    return MetricsResponse(**(sentiment_model.metrics or {}))


@app.get("/nlp/model/features", response_model=TopFeaturesResponse)
def top_features(k: int = 20):
    """The most heavily weighted terms, globally.

    A sanity check on training: if the strongest positive feature is something
    meaningless, the training data is wrong.
    """
    _require_ready()
    return TopFeaturesResponse(**sentiment_model.top_features(k=min(max(k, 1), 100)))


@app.get("/nlp/smote-stats", response_model=SmoteDistribution)
def smote_stats():
    dist = sentiment_model.smote_distribution or {}
    return SmoteDistribution(before=dist.get("before", {}), after=dist.get("after", {}))


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

@app.get("/nlp/tsne/before")
def tsne_before():
    return _send_plot("tsne_before.png")


@app.get("/nlp/tsne/after")
def tsne_after():
    return _send_plot("tsne_after.png")


def _send_plot(filename: str):
    path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{filename} not generated")
    return FileResponse(path, media_type="image/png")


@app.get("/nlp/health", response_model=HealthResponse)
def health():
    """Liveness and readiness.

    ``status`` reports the process is alive; ``ready`` reports the model is
    actually loaded. An orchestrator should gate traffic on ``ready`` and
    restarts on ``status``.
    """
    return HealthResponse(
        status="ok",
        model_loaded=sentiment_model.classifier is not None,
        vectorizer_loaded=sentiment_model.vectorizer is not None,
        modelVersion=MODEL_VERSION,
        ready=_ready,
    )
