import json

import chess
import joblib
import numpy as np
from datasets import Dataset

import app.pattern_training as training
from app.pattern import ATTACK_CLASSES
from app.pattern_features import FEATURE_NAMES


FENS = [
    chess.STARTING_FEN,
    "r1bq1rk1/ppp2ppp/2n5/3np3/2B1P3/2N2N2/PPP2PPP/R1BQ1RK1 w - - 0 9",
    "4k3/3p4/8/8/8/8/8/4K3 w - - 0 1",
    "r3k2r/ppp2ppp/8/8/8/8/PPP2PPP/R3K2R w KQkq - 0 1",
]


def test_evaluate_multilabel_shape_and_ranges():
    rng = np.random.default_rng(7)
    y_true = rng.integers(0, 2, size=(30, 23))
    y_score = rng.random((30, 23))
    metrics = training.evaluate_multilabel(y_true, y_score)

    assert set(metrics["per_class"]) == set(ATTACK_CLASSES)
    assert all(
        0 <= value["average_precision"] <= 1
        and 0 <= value["f1"] <= 1
        and value["support"] >= 0
        for value in metrics["per_class"].values()
    )
    assert 0 <= metrics["macro_f1"] <= 1
    assert 0 <= metrics["micro_f1"] <= 1


def test_pipeline_fit_produces_23_probabilities():
    rng = np.random.default_rng(11)
    labels = np.zeros((len(FENS) * 5, 23), dtype=int)
    for row in labels:
        row[rng.choice(23, size=3, replace=False)] = 1

    pipeline = training.build_pipeline()
    pipeline.fit(FENS * 5, labels)
    probabilities = pipeline.predict_proba(FENS)
    assert probabilities.shape == (len(FENS), 23)
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_main_writes_artifacts_without_network(tmp_path, monkeypatch):
    rng = np.random.default_rng(3)
    vectors = []
    for _ in range(60):
        vector = np.zeros(23, dtype=int)
        vector[rng.choice(23, size=3, replace=False)] = 1
        vectors.append(vector.tolist())
    dataset = Dataset.from_dict(
        {
            "FEN": FENS * 15,
            "label_vector": vectors,
            "GameId": [f"g{i % 4}" for i in range(60)],
        }
    )
    model_path = tmp_path / "pattern.joblib"
    metrics_path = tmp_path / "metrics.json"
    monkeypatch.setattr(training, "load_pattern_dataset", lambda limit: dataset)
    monkeypatch.setattr(training.config, "MODEL_PATH", model_path)
    monkeypatch.setattr(training.config, "METRICS_PATH", metrics_path)

    training.main([])

    artifact = joblib.load(model_path)
    assert set(artifact) == {"pipeline", "classes", "feature_names", "model_version"}
    assert artifact["classes"] == list(ATTACK_CLASSES)
    assert artifact["feature_names"] == list(FEATURE_NAMES)
    metrics = json.loads(metrics_path.read_text())
    assert set(metrics["per_class"]) == set(ATTACK_CLASSES)
    assert sum(item["support"] for item in metrics["per_class"].values()) > 0
    assert metrics["n_train"] + metrics["n_test"] == 60
