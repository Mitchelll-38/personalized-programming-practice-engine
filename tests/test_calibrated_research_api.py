import json
import math

from fastapi.testclient import TestClient
import pytest

from api.main import app
from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, payload_hash, save_rate_artifact
from practice_engine.models.bkt import BKTBaseline
from practice_engine.models.calibrated_artifacts import ValidationCalibrationRecord, save_calibrated_artifact
from practice_engine.models.calibration import TemperatureScaler
from practice_engine.models.logistic import LogisticBaseline
from practice_engine.models.portable import load_baseline_artifact, parse_baseline_artifact, save_baseline_artifact
from practice_engine.models.rates import RateBaseline
from practice_engine.models.serving import PredictionInput, predict_inputs


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("PRACTICE_RESEARCH_MODEL", raising=False)
    monkeypatch.setenv("PRACTICE_DB_PATH", str(tmp_path / "demo.sqlite3"))
    with TestClient(app) as client:
        yield client


def query():
    return {"student_id": "synthetic", "target_sequence_index": 0, "history": [],
            "candidate": {"problem_id": "new", "problem_text": "Synthetic sum", "concept_ids": ["loops"]}}


def prepared(tmp_path, monkeypatch, kind="rate", source="synthetic"):
    provenance = ArtifactProvenance(dataset_version="synthetic-calibration-v1", source_kind=source,
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    rows = [PredictionExample(student_id="fixture", target_sequence_index=0, history=(),
        candidate=Candidate(problem_id="known", problem_text="Synthetic sum", concept_ids=("loops",)), label=label)
        for label in (True, True, False)]
    path = tmp_path / "base.json"
    if kind == "rate":
        base = save_rate_artifact(path, RateBaseline.fit(rows), provenance)
    else:
        model = (LogisticBaseline if kind == "logistic" else BKTBaseline).fit(rows)
        base = save_baseline_artifact(path, model, provenance)
    record = ValidationCalibrationRecord(provenance=provenance, validation_sha256="c" * 64,
        probabilities_sha256="d" * 64, n_examples=2, temperature_grid=(1., 2.))
    path = tmp_path / "private-calibrated.json"
    wrapper = save_calibrated_artifact(path, base, TemperatureScaler(2.), record)
    monkeypatch.setenv("PRACTICE_RESEARCH_MODEL", str(path))
    return path, base, wrapper


@pytest.mark.parametrize("kind", ["rate", "logistic", "bkt"])
def test_calibrated_routes_bind_metadata_and_apply_scalar(client, tmp_path, monkeypatch, kind):
    path, base, wrapper = prepared(tmp_path, monkeypatch, kind)
    metadata = client.get("/research/model").json()
    assert metadata["calibrated"] is True and metadata["is_synthetic"] is True
    assert metadata["research_results"] is False and metadata["source_kind"] == "synthetic"
    assert metadata["model_kind"] == kind and metadata["model_sha256"] == base.model_sha256
    assert metadata["artifact_version"] == wrapper.artifact_version
    assert metadata["base_artifact_version"] == base.artifact_version
    assert metadata["base_artifact_sha256"] == payload_hash(base.model_dump())
    assert metadata["artifact_sha256"] == wrapper.artifact_sha256
    assert metadata["calibration"] == {"method": "temperature-scaling-v1", "temperature": 2.,
        "validation_record": wrapper.validation_record.model_dump(mode="json")}
    response = client.post("/research/predict", json={"inputs": [query()]})
    assert response.status_code == 200 and response.json()["model"] == metadata
    probability = predict_inputs(base, [PredictionInput.model_validate(query())])[0].predicted_correctness
    expected = math.sqrt(probability) / (math.sqrt(probability) + math.sqrt(1 - probability))
    if kind == "rate":
        assert probability == pytest.approx(.6)
    assert response.json()["predictions"] == [{"problem_id": "new", "predicted_correctness": pytest.approx(expected)}]
    assert str(path) not in response.text and "model_payload" not in response.text
    assert client.get("/models/current").json()["model_id"] == "demo-history-v1"
    assert client.post("/research/predict", json={"inputs": [{**query(), "label": True}]}).status_code == 422


@pytest.mark.parametrize("mutation", ["base", "temperature", "receipt", "provenance", "version", "unverified"])
def test_calibrated_errors_fail_closed(client, tmp_path, monkeypatch, mutation):
    path, _, _ = prepared(tmp_path, monkeypatch, source="unverified" if mutation == "unverified" else "synthetic")
    data = json.loads(path.read_text())
    if mutation == "base":
        data["base_artifact"]["model_payload"]["alpha"] = 5.
    elif mutation == "temperature":
        data["calibrator_payload"]["temperature"] = 1.
    elif mutation == "receipt":
        data["validation_record"]["probabilities_sha256"] = "e" * 64
    elif mutation == "provenance":
        data["validation_record"]["provenance"]["split_sha256"] = "e" * 64
        data["artifact_sha256"] = payload_hash({k: v for k, v in data.items() if k != "artifact_sha256"})
    elif mutation == "version":
        data["artifact_version"] = "future-calibrated-v1"
    path.write_text(json.dumps(data))
    for response in (client.get("/research/model"), client.post("/research/predict", json={"inputs": [query()]})):
        assert response.status_code == 503 and response.json() == {"detail": "research_model_unavailable"}
        assert str(path) not in response.text


def test_duplicate_nested_calibrated_field_fails_closed_on_public_routes(client, tmp_path, monkeypatch):
    path, _, _ = prepared(tmp_path, monkeypatch)
    serialized = path.read_text()
    old = '"source_kind": "synthetic"'
    assert old in serialized
    path.write_text(serialized.replace(old, '"source_kind": "unverified", ' + old, 1))
    for response in (client.get("/research/model"), client.post("/research/predict", json={"inputs": [query()]})):
        assert response.status_code == 503
        assert response.json() == {"detail": "research_model_unavailable"}
        assert str(path) not in response.text


def test_public_accessor_is_detached_validated_and_adapter_rechecks_live_integrity(tmp_path, monkeypatch):
    _, base, wrapper = prepared(tmp_path, monkeypatch)
    detached = wrapper.baseline()
    assert detached == base
    detached.model_payload["alpha"] = 5.
    assert wrapper.baseline() == base
    assert predict_inputs(wrapper, [PredictionInput.model_validate(query())])
    wrapper.calibrator_payload["temperature"] = 1.
    with pytest.raises(ValueError, match="hash"):
        wrapper.baseline()
    with pytest.raises(ValueError, match="hash"):
        predict_inputs(wrapper, [PredictionInput.model_validate(query())])


def test_public_parser_preserves_baseline_loader_and_rejects_calibrated_dispatch(tmp_path, monkeypatch):
    path, base, _ = prepared(tmp_path, monkeypatch)
    assert parse_baseline_artifact((tmp_path / "base.json").read_bytes()) == load_baseline_artifact(tmp_path / "base.json") == base
    for data in (b"[]", b"null", b"invalid JSON", path.read_bytes()):
        with pytest.raises(ValueError):
            parse_baseline_artifact(data)
