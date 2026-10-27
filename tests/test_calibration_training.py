from hashlib import sha256
import json
import subprocess
import sys

import pytest

from practice_engine.data.manifest import artifact_hashes
from practice_engine.data.schema import Interaction
from practice_engine.models.artifacts import payload_hash, save_rate_artifact
from practice_engine.models.bkt import BKTBaseline
from practice_engine.models.calibrated_artifacts import load_calibrated_artifact
from practice_engine.models.logistic import LogisticBaseline
from practice_engine.models.portable import save_baseline_artifact
from practice_engine.models.rates import RateBaseline
from practice_engine.training import calibration
from practice_engine.training.bundle import load_training_bundle


@pytest.fixture(params=["student", "family"])
def prepared(request, tmp_path):
    source, mapping, bundle = tmp_path / "source.jsonl", tmp_path / "families.json", tmp_path / "bundle"
    rows = [Interaction(student_id=f"s{s}", problem_id=f"p{p}", sequence_index=p,
        problem_text="Original synthetic sum", concept_ids=("loops",), correct=p % 2 == 0, attempt_number=1)
        for s in range(6) for p in range(6)]
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows))
    mapping.write_text(json.dumps({f"p{p}": f"f{p // 2}" for p in range(6)}))
    flags = ["--split-protocol", request.param]
    if request.param == "family":
        flags += ["--family-map", str(mapping)]
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source), "--synthetic",
                    "--output", str(bundle), *flags], check=True, capture_output=True)
    return bundle, load_training_bundle(bundle)


def base_model(tmp_path, verified, kind="rate"):
    path = tmp_path / "base.json"
    if kind == "rate":
        return path, save_rate_artifact(path, RateBaseline.fit(verified.train), verified.provenance)
    model_class = LogisticBaseline if kind == "logistic" else BKTBaseline
    return path, save_baseline_artifact(path, model_class.fit(verified.train), verified.provenance)


def rehash(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    (bundle / "manifest.json").write_text(json.dumps(manifest))


@pytest.mark.parametrize("kind", ["rate", "logistic", "bkt"])
def test_fitting_receipts_reload_and_test_is_never_parsed(prepared, tmp_path, kind, monkeypatch):
    bundle, verified = prepared
    path, base = base_model(tmp_path, verified, kind)
    def forbidden_refit(*args, **kwargs):
        raise AssertionError("Calibration must not refit the fixed base model")
    for model_class in (RateBaseline, LogisticBaseline, BKTBaseline):
        monkeypatch.setattr(model_class, "fit", forbidden_refit)
    base_bytes = path.read_bytes()
    first = calibration.calibrate_baseline(bundle, path, tmp_path / "before")
    (bundle / "test.jsonl").write_bytes(b"\xffPOISON: never parse locked test")
    rehash(bundle)
    second = calibration.calibrate_baseline(bundle, path, tmp_path / "after")
    one = load_calibrated_artifact(tmp_path / "before/model.json")
    two = load_calibrated_artifact(tmp_path / "after/model.json")
    assert one == two and first["test_evaluated"] is second["test_evaluated"] is False
    assert path.read_bytes() == base_bytes
    assert first["reload_predictions_equal"] is True and first["research_results"] is False
    assert first["evaluation_role"] == "same-validation-observations-used-for-calibration"
    record = one.validation_record
    assert record.validation_sha256 == sha256((bundle / "validation.jsonl").read_bytes()).hexdigest()
    assert record.probabilities_sha256 == payload_hash({"probabilities": base.predict(verified.validation)})
    assert record.provenance == verified.provenance
    for filename in ("model.json", "validation.json", "reliability.json"):
        assert (tmp_path / "before" / filename).read_bytes() == (tmp_path / "after" / filename).read_bytes()
    assert first["processing_manifest_sha256"] != second["processing_manifest_sha256"]
    assert {p.name for p in (tmp_path / "before").iterdir()} == {"model.json", "run.json", "validation.json", "reliability.json"}


def test_calibration_receipt_hashes_consumed_validation_bytes(prepared, tmp_path, monkeypatch):
    bundle, verified = prepared
    path, base = base_model(tmp_path, verified)
    original_digest = verified.manifest.artifact_sha256["validation.jsonl"]
    original_fit = calibration.TemperatureScaler.fit_validation

    def fit_then_change_file(cls, examples, probabilities, *, temperatures):
        fitted = original_fit(examples, probabilities, temperatures=temperatures)
        validation_path = bundle / "validation.jsonl"
        validation_path.write_bytes(validation_path.read_bytes() + b"\n")
        return fitted

    monkeypatch.setattr(calibration.TemperatureScaler, "fit_validation", classmethod(fit_then_change_file))
    calibration.calibrate_baseline(bundle, path, tmp_path / "calibrated")
    artifact = load_calibrated_artifact(tmp_path / "calibrated/model.json")
    assert artifact.validation_record.validation_sha256 == original_digest
    assert artifact.validation_record.validation_sha256 != sha256((bundle / "validation.jsonl").read_bytes()).hexdigest()
    assert artifact.validation_record.probabilities_sha256 == payload_hash(
        {"probabilities": base.predict(verified.validation)})
    assert artifact.predict(verified.validation)


def test_mismatched_model_and_unverified_bundle_rejected(prepared, tmp_path):
    bundle, verified = prepared
    path, base = base_model(tmp_path, verified)
    changed = base.provenance.model_copy(update={"split_sha256": "e" * 64})
    save_rate_artifact(path, RateBaseline.fit(verified.train), changed)
    with pytest.raises(ValueError, match="provenance"):
        calibration.calibrate_baseline(bundle, path, tmp_path / "bad")
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["source_kind"] = "unverified"
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="synthetic"):
        calibration.calibrate_baseline(bundle, path, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_grid_errors_existing_output_and_failed_reload_preserve_runs(prepared, tmp_path, monkeypatch):
    bundle, verified = prepared
    path, _ = base_model(tmp_path, verified)
    for grid in ((), (1., 1.), (float("nan"),), (True,)):
        with pytest.raises(ValueError):
            calibration.calibrate_baseline(bundle, path, tmp_path / "bad", temperatures=grid)
    run = tmp_path / "existing"
    run.mkdir()
    (run / "keep").write_text("preserved")
    with pytest.raises(ValueError, match="new directory"):
        calibration.calibrate_baseline(bundle, path, run)
    assert (run / "keep").read_text() == "preserved"
    def failed(*args):
        raise ValueError("reload failed")
    monkeypatch.setattr(calibration, "load_calibrated_artifact", failed)
    with pytest.raises(ValueError, match="reload failed"):
        calibration.calibrate_baseline(bundle, path, tmp_path / "runs/failed")
    assert list((tmp_path / "runs").iterdir()) == []


def test_cli_records_explicit_grid(prepared, tmp_path):
    bundle, verified = prepared
    path, _ = base_model(tmp_path, verified)
    result = subprocess.run([sys.executable, "-m", "practice_engine.training.calibration", str(bundle),
        "--base-model", str(path), "--output", str(tmp_path / "cli"), "--temperatures", "1", "2"],
        check=True, capture_output=True, text=True)
    run = json.loads(result.stdout)
    assert run["temperature_grid"] == [1., 2.]
    assert run["calibration_fit_partition"] == run["evaluated_partition"] == "validation"


def test_one_class_validation_fails_before_publication(prepared, tmp_path):
    bundle, verified = prepared
    path, _ = base_model(tmp_path, verified)
    rows = [json.loads(line) for line in (bundle / "validation.jsonl").read_text().splitlines()]
    for row in rows:
        row["label"] = True
    validation_targets = {(row["student_id"], row["target_sequence_index"]) for row in rows}
    for row in rows:
        for observed in row["history"]:
            if (row["student_id"], observed["sequence_index"]) in validation_targets:
                observed["correct"] = True
    (bundle / "validation.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    rehash(bundle)
    with pytest.raises(ValueError, match="both validation classes"):
        calibration.calibrate_baseline(bundle, path, tmp_path / "single-class")
    assert not (tmp_path / "single-class").exists()
