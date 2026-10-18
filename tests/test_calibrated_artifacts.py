import json

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, payload_hash, save_rate_artifact
from practice_engine.models.bkt import BKTBaseline
from practice_engine.models.calibrated_artifacts import (
    ValidationCalibrationRecord, load_calibrated_artifact, save_calibrated_artifact,
)
from practice_engine.models.calibration import TemperatureScaler
from practice_engine.models.logistic import LogisticBaseline
from practice_engine.models.portable import save_baseline_artifact
from practice_engine.models.rates import RateBaseline


@pytest.fixture(params=["rate", "logistic", "bkt"])
def fitted(request, tmp_path):
    rows = [PredictionExample(student_id="synthetic", target_sequence_index=i, history=(), label=label,
        candidate=Candidate(problem_id=f"p{i}", problem_text="Synthetic sum", concept_ids=("loops",)))
        for i, label in enumerate((True, True, False))]
    provenance = ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    if request.param == "rate":
        base = save_rate_artifact(tmp_path / "base.json", RateBaseline.fit(rows), provenance)
    else:
        model = (LogisticBaseline if request.param == "logistic" else BKTBaseline).fit(rows)
        base = save_baseline_artifact(tmp_path / "base.json", model, provenance)
    record = ValidationCalibrationRecord(provenance=provenance, validation_sha256="c" * 64,
        probabilities_sha256="d" * 64, n_examples=3, temperature_grid=(1., 2., 3.))
    return base, rows, record


def test_reload_parity_and_detached_live_payloads(fitted, tmp_path):
    base, rows, record = fitted
    scaler = TemperatureScaler(2.)
    path = tmp_path / "calibrated.json"
    saved = save_calibrated_artifact(path, base, scaler, record)
    loaded = load_calibrated_artifact(path)
    assert loaded == saved
    assert loaded.calibrated is True
    assert loaded.base_artifact_sha256 == payload_hash(base.model_dump())
    assert loaded.predict(rows) == scaler.predict(base.predict(rows))
    assert loaded.predict([]) == []
    base.model_payload.clear()
    assert loaded.predict(rows) == saved.predict(rows)
    loaded.calibrator_payload["temperature"] = 3.
    with pytest.raises(ValueError, match="envelope hash"):
        loaded.predict(rows)


def test_base_and_split_mismatch_fail_before_publication(fitted, tmp_path):
    base, _, record = fitted
    mismatch = record.model_copy(update={"provenance": record.provenance.model_copy(update={"split_sha256": "e" * 64})})
    with pytest.raises(ValueError, match="provenance"):
        save_calibrated_artifact(tmp_path / "bad.json", base, TemperatureScaler(2.), mismatch)
    with pytest.raises(ValueError, match="fitting grid"):
        save_calibrated_artifact(tmp_path / "bad.json", base, TemperatureScaler(4.), record)
    assert not (tmp_path / "bad.json").exists()


def test_corruption_and_unsupported_versions_rejected(fitted, tmp_path):
    base, _, record = fitted
    path = tmp_path / "calibrated.json"
    saved = save_calibrated_artifact(path, base, TemperatureScaler(2.), record)
    for field, value in [("artifact_version", "future"), ("calibrated", False), ("artifact_sha256", "0" * 64)]:
        payload = json.loads(saved.model_dump_json())
        payload[field] = value
        path.write_text(json.dumps(payload))
        with pytest.raises(ValueError):
            load_calibrated_artifact(path)
    saved.base_artifact["provenance"]["dataset_version"] = "changed"
    with pytest.raises(ValueError):
        saved.predict([])


@pytest.mark.parametrize("change", [
    {"temperature_grid": ()}, {"temperature_grid": (1., 1.)}, {"temperature_grid": (True,)},
    {"temperature_grid": (float("inf"),)}, {"n_examples": True}, {"n_examples": 0},
    {"fit_partition": "test"}, {"validation_sha256": "not-a-hash"},
])
def test_invalid_validation_record_rejected(fitted, change):
    _, _, record = fitted
    with pytest.raises(ValueError):
        ValidationCalibrationRecord.model_validate({**record.model_dump(), **change})


def test_atomic_failure_preserves_previous_artifact(fitted, tmp_path, monkeypatch):
    base, _, record = fitted
    path = tmp_path / "calibrated.json"
    save_calibrated_artifact(path, base, TemperatureScaler(2.), record)
    previous = path.read_bytes()
    def interrupted(*args):
        raise OSError("interrupted publication")
    monkeypatch.setattr("practice_engine.models.artifacts.os.replace", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        save_calibrated_artifact(path, base, TemperatureScaler(3.), record)
    assert path.read_bytes() == previous
    assert {p.name for p in tmp_path.iterdir()} == {"base.json", "calibrated.json"}
