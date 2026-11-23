"""Training pipeline, multi-label evaluation and artifact writing."""

from __future__ import annotations

import argparse
import json

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app import config
from app.pattern import ATTACK_CLASSES, load_pattern_dataset, split_by_game_id
from app.pattern_features import FEATURE_NAMES, PatternFeatureExtractor


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("features", PatternFeatureExtractor()),
            ("scaler", StandardScaler()),
            (
                "classifier",
                OneVsRestClassifier(LogisticRegression(solver="liblinear", max_iter=1000)),
            ),
        ]
    )


def evaluate_multilabel(y_true, y_score) -> dict:
    """Per-class average precision, F1 and support, plus macro/micro F1."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    y_pred = (y_score >= 0.5).astype(int)

    # sklearn's AP has no zero_division: an absent class has no AP by definition.
    ap = np.zeros(len(ATTACK_CLASSES))
    for index in range(len(ATTACK_CLASSES)):
        if y_true[:, index].sum():
            ap[index] = average_precision_score(y_true[:, index], y_score[:, index])

    per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    per_class = {
        name: {
            "average_precision": float(ap[index]),
            "f1": float(per_class_f1[index]),
            "support": int(y_true[:, index].sum()),
        }
        for index, name in enumerate(ATTACK_CLASSES)
    }
    return {
        "per_class": per_class,
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "micro_f1": float(f1_score(y_true, y_pred, average="micro", zero_division=0)),
        "model_version": config.MODEL_VERSION,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        type=int,
        default=200000,
        help="number of filtered rows to use; 0 means all rows",
    )
    args = parser.parse_args(argv)

    dataset = load_pattern_dataset(limit=args.sample)
    train, test = split_by_game_id(dataset)
    # The dataset column is already the 23-wide binary vector from pattern.py.
    y_train = np.asarray(train["label_vector"], dtype=np.int8)
    y_test = np.asarray(test["label_vector"], dtype=np.int8)

    pipeline = build_pipeline()
    pipeline.fit(train["FEN"], y_train)
    scores = pipeline.predict_proba(test["FEN"])

    metrics = evaluate_multilabel(y_test, scores)
    metrics["n_train"] = len(train)
    metrics["n_test"] = len(test)

    artifact = {
        "pipeline": pipeline,
        "classes": list(ATTACK_CLASSES),
        "feature_names": list(FEATURE_NAMES),
        "model_version": config.MODEL_VERSION,
    }
    config.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, config.MODEL_PATH)
    config.METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    print(f"train={len(train)} test={len(test)}")
    print(f"macro_f1={metrics['macro_f1']:.3f} micro_f1={metrics['micro_f1']:.3f}")
    print(f"model: {config.MODEL_PATH}")
    print(f"metrics: {config.METRICS_PATH}")


if __name__ == "__main__":
    main()
