from hashlib import sha256
import json
import subprocess
import sys

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.inference_profile import _timings, profile_inference
from practice_engine.models.artifacts import ArtifactProvenance, save_rate_artifact
from practice_engine.models.calibrated_artifacts import ValidationCalibrationRecord, save_calibrated_artifact
from practice_engine.models.calibration import TemperatureScaler
from practice_engine.models.rates import RateBaseline


@pytest.fixture
def prepared(tmp_path):
    provenance = ArtifactProvenance(dataset_version="synthetic-profile-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    row = PredictionExample(student_id="synthetic", target_sequence_index=0, history=(), label=True,
        candidate=Candidate(problem_id="known", problem_text="Original synthetic", concept_ids=("loops",)))
    model = tmp_path / "model.json"
    base = save_rate_artifact(model, RateBaseline.fit([row]), provenance)
    queries = tmp_path / "queries.json"
    queries.write_text(json.dumps({"inputs": [row.model_dump(exclude={"label"})]}))
    return model, queries, base


def test_profile_binds_exact_files_and_reports_aggregate_scope_without_fitting(prepared, monkeypatch):
    model, queries, _ = prepared
    original = (model.read_bytes(), queries.read_bytes())
    def forbidden(*args, **kwargs):
        raise AssertionError("Profiling must not fit")
    monkeypatch.setattr(RateBaseline, "fit", forbidden)
    report = profile_inference(model, queries, repeats=3, warmups=1)
    assert report["artifact_sha256"] == sha256(original[0]).hexdigest()
    assert report["queries_sha256"] == sha256(original[1]).hexdigest()
    assert report["batch_size"] == 1 and report["repeats"] == 3 and report["warmups"] == 1
    assert report["calibrated"] is False and report["research_results"] is False
    assert report["batch_ms"]["min"] <= report["batch_ms"]["median"] <= report["batch_ms"]["p95"] <= report["batch_ms"]["max"]
    assert report["queries_per_second"] > 0
    assert "Original synthetic" not in json.dumps(report) and "predictions" not in report
    assert (model.read_bytes(), queries.read_bytes()) == original


def test_calibrated_envelope_and_cli_profile_without_outputs(prepared, tmp_path):
    model, queries, base = prepared
    record = ValidationCalibrationRecord(provenance=base.provenance, validation_sha256="c" * 64,
        probabilities_sha256="d" * 64, n_examples=2, temperature_grid=(1., 2.))
    calibrated = tmp_path / "calibrated.json"
    save_calibrated_artifact(calibrated, base, TemperatureScaler(2.), record)
    report = profile_inference(calibrated, queries, repeats=1, warmups=0)
    assert report["calibrated"] is True and report["artifact_version"] == "temperature-baseline-artifact-v1"
    result = subprocess.run([sys.executable, "-m", "practice_engine.inference_profile", str(model), str(queries),
        "--repeats", "1", "--warmups", "0"], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["batch_size"] == 1


@pytest.mark.parametrize("updates", [{"repeats": True}, {"repeats": 0}, {"repeats": 1001},
    {"warmups": True}, {"warmups": -1}, {"warmups": 101}])
def test_invalid_run_bounds_fail_before_file_reads(updates):
    with pytest.raises(ValueError):
        profile_inference("missing", "missing", **updates)


@pytest.mark.parametrize("mutate", [lambda row: row.update(label=True),
    lambda row: row["candidate"].update(submitted_code="target poison"),
    lambda row: row.update(history=[{"invalid": "future"}])])
def test_target_and_bad_history_fail_before_timed_prediction(prepared, monkeypatch, mutate):
    model, queries, _ = prepared
    body = json.loads(queries.read_text())
    mutate(body["inputs"][0])
    queries.write_text(json.dumps(body))
    def forbidden(*args):
        raise AssertionError("Invalid input reached prediction")
    monkeypatch.setattr("practice_engine.inference_profile.predict_inputs", forbidden)
    with pytest.raises(ValueError):
        profile_inference(model, queries)


def test_tampered_artifact_rejected(prepared):
    model, queries, _ = prepared
    body = json.loads(model.read_text())
    body["model_payload"]["alpha"] = 9
    model.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        profile_inference(model, queries)


def test_nearest_rank_and_zero_clock_resolution():
    assert _timings([10, 30, 20, 40], 2) == {
        "batch_ms": {"min": .00001, "median": .000025, "p95": .00004, "max": .00004},
        "queries_per_second": 80_000_000.}
    assert _timings([0], 1)["queries_per_second"] is None


@pytest.mark.parametrize("kind", ["unverified-source", "empty-batch", "oversized-batch", "oversized-history"])
def test_source_and_query_bounds_fail_closed(prepared, kind):
    model, queries, base = prepared
    if kind == "unverified-source":
        payload = json.loads(model.read_text())
        payload["provenance"]["source_kind"] = "unverified"
        model.write_text(json.dumps(payload))
    else:
        body = json.loads(queries.read_text())
        if kind == "empty-batch":
            body["inputs"] = []
        elif kind == "oversized-batch":
            body["inputs"] *= 1001
        else:
            body["inputs"][0]["history"] = [{}] * 10001
        queries.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        profile_inference(model, queries)
