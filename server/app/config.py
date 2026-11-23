"""Paths and settings for the pattern model. Override with CHESS_* env vars."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_VERSION = "0.1.0"
MODEL_PATH = Path(
    os.environ.get("CHESS_PATTERN_MODEL", BASE_DIR / "models" / "pattern.joblib")
)
METRICS_PATH = Path(
    os.environ.get(
        "CHESS_PATTERN_METRICS", BASE_DIR / "models" / "pattern_metrics.json"
    )
)
FALLBACK_MODEL_VERSION = os.environ.get("CHESS_PATTERN_MODEL_VERSION", MODEL_VERSION)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CHESS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
