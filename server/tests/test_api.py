import chess
import joblib
import numpy as np
from fastapi.testclient import TestClient

from app.api import ArtifactUnavailable, PatternClassifier, create_app
from app.pattern import ATTACK_CLASSES
from app.pattern_features import FEATURE_NAMES


class StubPipeline:
    def predict_proba(self, X):
        return np.tile(np.linspace(0, 1, 23), (len(X), 1))


class FakeClassifier:
    def __init__(self):
        self.fens = []

    def predict(self, fen):
        self.fens.append(fen)
        scores = [(name, 0.01) for name in ATTACK_CLASSES]
        scores[ATTACK_CLASSES.index("fork")] = ("fork", 0.9)
        scores[ATTACK_CLASSES.index("mate")] = ("mate", 0.5)
        return scores, "test-version"


def test_health():
    with TestClient(create_app(PatternClassifier())) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prediction_has_23_sorted_independent_labels():
    fake = FakeClassifier()
    with TestClient(create_app(fake)) as client:
        response = client.post("/api/analyze-pattern", json={"fen": chess.STARTING_FEN})

    assert response.status_code == 200
    data = response.json()
    assert data["model_version"] == "test-version"
    assert len(data["labels"]) == 23
    assert [item["label"] for item in data["labels"][:2]] == ["fork", "mate"]
    probabilities = [item["probability"] for item in data["labels"]]
    assert probabilities == sorted(probabilities, reverse=True)
    assert all(0.0 <= value <= 1.0 for value in probabilities)
    assert sum(probabilities) != 1.0
    assert fake.fens == [chess.STARTING_FEN]


def test_invalid_fen_and_body_are_422():
    with TestClient(create_app(FakeClassifier())) as client:
        for payload in (
            {"fen": "not-a-fen"},
            {"fen": "8/8/8/8/8/8/8/8 w - - 0 1"},
            {},
            {"fen": 123},
        ):
            assert client.post("/api/analyze-pattern", json=payload).status_code == 422


def test_missing_corrupt_and_stale_artifact_are_503(tmp_path):
    with TestClient(create_app(PatternClassifier(tmp_path / "missing.joblib"))) as client:
        response = client.post("/api/analyze-pattern", json={"fen": chess.STARTING_FEN})
        assert response.status_code == 503
        # The server stays alive after a failed prediction.
        assert client.get("/api/health").status_code == 200

    corrupt = tmp_path / "corrupt.joblib"
    corrupt.write_bytes(b"not a joblib artifact")
    with TestClient(create_app(PatternClassifier(corrupt))) as client:
        assert (
            client.post("/api/analyze-pattern", json={"fen": chess.STARTING_FEN}).status_code
            == 503
        )

    stale = tmp_path / "stale.joblib"
    joblib.dump(
        {
            "pipeline": None,
            "classes": list(ATTACK_CLASSES),
            "feature_names": list(reversed(FEATURE_NAMES)),
            "model_version": "0.1.0",
        },
        stale,
    )
    with TestClient(create_app(PatternClassifier(stale))) as client:
        assert (
            client.post("/api/analyze-pattern", json={"fen": chess.STARTING_FEN}).status_code
            == 503
        )


def test_cors_allows_frontend_origins():
    with TestClient(create_app(FakeClassifier())) as client:
        allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        blocked = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers


def test_artifact_unavailable_is_distinct_from_bad_fen():
    assert issubclass(ArtifactUnavailable, Exception)


def test_real_artifact_prediction_end_to_end(tmp_path):
    import numpy as np

    from app.pattern_training import build_pipeline

    fens = [
        chess.STARTING_FEN,
        "r4rk1/pp3ppp/8/2bqp2b/3N4/P2Bn2P/1PPN1P2/R1BQ1RK1 w - - 1 15",
    ] * 4
    rng = np.random.default_rng(5)
    labels = rng.integers(0, 2, size=(len(fens), 23))
    pipeline = build_pipeline()
    pipeline.fit(fens, labels)

    artifact_path = tmp_path / "pattern.joblib"
    joblib.dump(
        {
            "pipeline": pipeline,
            "classes": list(ATTACK_CLASSES),
            "feature_names": list(FEATURE_NAMES),
            "model_version": "0.1.0",
        },
        artifact_path,
    )

    with TestClient(create_app(PatternClassifier(artifact_path))) as client:
        response = client.post("/api/analyze-pattern", json={"fen": fens[1]})
    assert response.status_code == 200
    assert len(response.json()["labels"]) == 23


def test_missing_artifact_version_uses_config_fallback(tmp_path, monkeypatch):
    from app import config

    artifact_path = tmp_path / "no-version.joblib"
    joblib.dump(
        {
            "pipeline": StubPipeline(),
            "classes": list(ATTACK_CLASSES),
            "feature_names": list(FEATURE_NAMES),
        },
        artifact_path,
    )
    monkeypatch.setattr(config, "FALLBACK_MODEL_VERSION", "fallback-9")

    with TestClient(create_app(PatternClassifier(artifact_path))) as client:
        response = client.post(
            "/api/analyze-pattern", json={"fen": chess.STARTING_FEN}
        )
    assert response.status_code == 200
    assert response.json()["model_version"] == "fallback-9"
