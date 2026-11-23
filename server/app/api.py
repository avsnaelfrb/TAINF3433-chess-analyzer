"""FastAPI contract: health check and multi-label pattern prediction."""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter

import chess
import joblib
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import config
from app.pattern_features import FEATURE_NAMES

logger = logging.getLogger(__name__)

# model_version is optional in the artifact: config.FALLBACK_MODEL_VERSION covers it.
ARTIFACT_KEYS = ("pipeline", "classes", "feature_names")


class ArtifactUnavailable(Exception):
    """Raised when the model cannot be loaded or no longer matches the code."""


class AnalyzeRequest(BaseModel):
    fen: str = Field(..., min_length=1)


class LabelScore(BaseModel):
    label: str
    probability: float


class AnalyzeResponse(BaseModel):
    labels: list[LabelScore]
    model_version: str


class PatternClassifier:
    """Loads the artifact on first use so the app can start without it."""

    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path) if model_path is not None else config.MODEL_PATH
        self._artifact: dict | None = None
        self._failure: str | None = None

    def _load(self) -> dict:
        if self._artifact is not None:
            return self._artifact
        if self._failure is not None:
            raise ArtifactUnavailable(self._failure)
        if not self.model_path.exists():
            self._fail("Model artifact is not available")
        try:
            artifact = joblib.load(self.model_path)
            if not isinstance(artifact, dict) or any(
                key not in artifact for key in ARTIFACT_KEYS
            ):
                raise ValueError("incomplete artifact")
            if list(artifact["feature_names"]) != list(FEATURE_NAMES):
                raise ValueError("stale feature list")
        except Exception:
            self._fail("Model artifact is corrupt or stale")
        self._artifact = artifact
        return artifact

    def _fail(self, message: str) -> None:
        self._failure = message
        raise ArtifactUnavailable(message)

    def predict(self, fen: str) -> tuple[list[tuple[str, float]], str]:
        artifact = self._load()
        # The pipeline starts with the extractor: it expects FEN strings, not vectors.
        probabilities = artifact["pipeline"].predict_proba([fen])[0]
        classes = artifact["classes"]
        if len(probabilities) != len(classes):
            self._artifact = None
            self._fail("Model artifact is corrupt or stale")
        scores = [(str(label), float(value)) for label, value in zip(classes, probabilities)]
        version = str(artifact.get("model_version") or config.FALLBACK_MODEL_VERSION)
        return scores, version


def create_app(pattern_classifier: PatternClassifier | None = None) -> FastAPI:
    app = FastAPI(title="Chess Pattern Analyzer")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.pattern_classifier = (
        pattern_classifier if pattern_classifier is not None else PatternClassifier()
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = perf_counter()
        response = await call_next(request)
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - start) * 1000,
        )
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/analyze-pattern", response_model=AnalyzeResponse)
    def analyze_pattern(body: AnalyzeRequest, request: Request):
        try:
            board = chess.Board(body.fen)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid FEN") from None
        if board.status() != chess.STATUS_VALID:
            raise HTTPException(status_code=422, detail="Invalid FEN")

        try:
            scores, version = request.app.state.pattern_classifier.predict(body.fen)
        except ArtifactUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None

        labels = [
            {"label": name, "probability": probability} for name, probability in scores
        ]
        # Stable sort keeps ATTACK_CLASSES order for ties.
        labels.sort(key=lambda item: -item["probability"])
        return {"labels": labels, "model_version": version}

    return app
