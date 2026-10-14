import json

from fastapi.testclient import TestClient
import pytest

from api.main import app
from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, save_rate_artifact
from practice_engine.models.bkt import BKTBaseline
from practice_engine.models.logistic import LogisticBaseline
from practice_engine.models.portable import save_baseline_artifact
from practice_engine.models.rates import RateBaseline


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("PRACTICE_RESEARCH_MODEL", raising=False)
    monkeypatch.setenv("PRACTICE_DB_PATH", str(tmp_path / "demo.sqlite3"))
    with TestClient(app) as client:
        yield client


def query(problem="unknown"):
    return {"student_id": "synthetic", "target_sequence_index": 0, "history": [],
            "candidate": {"problem_id": problem, "problem_text": "Synthetic exercise", "concept_ids": ["loops"]}}


def artifact(tmp_path, monkeypatch, kind="rate", source="synthetic"):
    provenance = ArtifactProvenance(dataset_version="synthetic-fixture-v1", source_kind=source,
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    examples = [PredictionExample(student_id="fixture", target_sequence_index=0, history=(),
        candidate=Candidate(problem_id="known", problem_text="Synthetic exercise", concept_ids=("loops",)), label=label)
        for label in (True, True, False)]
    path = tmp_path / "private-model.json"
    if kind == "rate":
        saved = save_rate_artifact(path, RateBaseline.fit(examples), provenance)
    else:
        model_class = LogisticBaseline if kind == "logistic" else BKTBaseline
        saved = save_baseline_artifact(path, model_class.fit(examples), provenance)
    monkeypatch.setenv("PRACTICE_RESEARCH_MODEL", str(path))
    return path, saved


def test_unconfigured_routes_and_demo_remain_separate(client, tmp_path, monkeypatch):
    for response in (client.get("/research/model"), client.post("/research/predict", json={"inputs": [query()]})):
        assert response.status_code == 503
        assert response.json() == {"detail": "research_model_not_configured"}
    before = client.post("/predict", json={"history": [], "candidate_ids": ["java-sum"]}).json()
    artifact(tmp_path, monkeypatch)
    assert client.get("/models/current").json()["model_id"] == "demo-history-v1"
    assert client.post("/predict", json={"history": [], "candidate_ids": ["java-sum"]}).json() == before


@pytest.mark.parametrize("kind", ["rate", "logistic", "bkt"])
def test_baseline_metadata_prediction_order_and_no_persistence(client, tmp_path, monkeypatch, kind):
    path, saved = artifact(tmp_path, monkeypatch, kind)
    before = client.get("/students/demo/history").json()
    metadata = client.get("/research/model").json()
    assert metadata["model_kind"] == kind
    assert metadata["model_sha256"] == saved.model_sha256
    assert metadata["provenance"] == saved.provenance.model_dump()
    assert metadata["is_synthetic"] is True
    assert metadata["calibrated"] is metadata["research_results"] is False
    response = client.post("/research/predict", json={"inputs": [query("z"), query("a")]})
    assert response.status_code == 200
    assert response.json()["model"] == metadata
    predictions = response.json()["predictions"]
    assert [row["problem_id"] for row in predictions] == ["z", "a"]
    assert all(0 <= row["predicted_correctness"] <= 1 for row in predictions)
    if kind == "rate":
        assert [row["predicted_correctness"] for row in predictions] == pytest.approx([.6, .6])
    assert client.get("/students/demo/history").json() == before
    assert str(path) not in response.text and "model_payload" not in response.text


@pytest.mark.parametrize("failure", ["missing", "malformed", "tampered", "unverified", "unsupported"])
def test_invalid_artifacts_fail_closed_without_private_error_details(client, tmp_path, monkeypatch, failure):
    path, _ = artifact(tmp_path, monkeypatch, source="unverified" if failure == "unverified" else "synthetic")
    if failure == "missing":
        path.unlink()
    elif failure == "malformed":
        path.write_text("private payload not JSON")
    elif failure in ("tampered", "unsupported"):
        data = json.loads(path.read_text())
        if failure == "tampered":
            data["model_payload"]["alpha"] = 5.0
        else:
            data["artifact_version"] = "unknown"
        path.write_text(json.dumps(data))
    for response in (client.get("/research/model"), client.post("/research/predict", json={"inputs": [query()]})):
        assert response.status_code == 503
        assert response.json() == {"detail": "research_model_unavailable"}
        assert str(path) not in response.text and "private payload" not in response.text


def test_artifact_replacement_is_not_cached(client, tmp_path, monkeypatch):
    path, _ = artifact(tmp_path, monkeypatch)
    assert client.get("/research/model").status_code == 200
    path.write_text("replaced invalid artifact")
    assert client.get("/research/model").status_code == 503


@pytest.mark.parametrize("location", ["wrapper", "query", "candidate"])
def test_target_response_injection_rejected(client, location):
    body = {"inputs": [query()]}
    target = body if location == "wrapper" else body["inputs"][0]
    if location == "candidate":
        target = target["candidate"]
    target["label"] = True
    assert client.post("/research/predict", json=body).status_code == 422


def test_bounds_and_candidate_response_in_history_rejected(client):
    for inputs in ([], [query()] * 1001):
        assert client.post("/research/predict", json={"inputs": inputs}).status_code == 422
    row = query()
    row["history"] = [{}] * 10001
    response = client.post("/research/predict", json={"inputs": [row]})
    assert response.status_code == 422 and "10000" in response.text
    row["target_sequence_index"] = 1
    row["history"] = [{"student_id": "synthetic", "problem_id": "unknown", "sequence_index": 0,
        "problem_text": "Synthetic prior", "concept_ids": ["loops"], "correct": True, "attempt_number": 1}]
    assert client.post("/research/predict", json={"inputs": [row]}).status_code == 422
