"""Synthetic changes to a valid bundle identity must not publish mixed receipts."""

from hashlib import sha256
import json
import subprocess
import sys

import pytest

from practice_engine.data.schema import Interaction
from practice_engine.training import baselines, calibration, dkt, rates


@pytest.fixture
def bundle(tmp_path):
    source = tmp_path / "source.jsonl"
    rows = [Interaction(student_id=f"s{student}", problem_id=f"p{problem}",
                        sequence_index=problem, problem_text="Synthetic exercise",
                        concept_ids=("loops",), correct=problem % 2 == 0, attempt_number=1)
            for student in range(6) for problem in range(6)]
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows))
    directory = tmp_path / "bundle"
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source),
                    "--synthetic", "--output", str(directory)], capture_output=True, check=True)
    return directory


def change_manifest_version(bundle):
    path = bundle / "manifest.json"
    payload = json.loads(path.read_text())
    payload["dataset_version"] = "synthetic-changed-during-fit"
    path.write_text(json.dumps(payload))


def test_manifest_change_during_bundle_load_prevents_publication(bundle, tmp_path, monkeypatch):
    original = rates.load_training_bundle

    def load_then_change(path):
        verified = original(path)
        change_manifest_version(bundle)
        return verified

    monkeypatch.setattr(rates, "load_training_bundle", load_then_change)
    output = tmp_path / "rejected-run"
    with pytest.raises(ValueError, match="Processing manifest changed during verification"):
        rates.train_rates(bundle, output)
    assert not output.exists()


def test_manifest_restored_after_loader_cannot_mislabel_run(bundle, tmp_path, monkeypatch):
    """The verifier must return B's bytes even when the file is A afterward."""
    path = bundle / "manifest.json"
    original_bytes = path.read_bytes()
    changed = json.loads(original_bytes)
    changed["dataset_version"] = "synthetic-temporary-version"
    changed_bytes = json.dumps(changed).encode()
    original_load = rates.load_training_bundle

    def load_temporary_version(directory):
        path.write_bytes(changed_bytes)
        verified = original_load(directory)
        assert verified.manifest_bytes == changed_bytes
        assert verified.manifest.dataset_version == "synthetic-temporary-version"
        path.write_bytes(original_bytes)
        return verified

    monkeypatch.setattr(rates, "load_training_bundle", load_temporary_version)
    output = tmp_path / "rejected-run"
    with pytest.raises(ValueError, match="Processing manifest changed during verification"):
        rates.train_rates(bundle, output)
    assert path.read_bytes() == original_bytes
    assert not output.exists()


@pytest.mark.parametrize("kind", ["rate", "bkt", "logistic", "dkt", "calibration"])
def test_manifest_change_during_fit_prevents_publication(bundle, tmp_path, monkeypatch, kind):
    initial_hash = sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    if kind == "rate":
        module, owner, method = rates, rates.RateBaseline, "fit"
        run = lambda output: module.train_rates(bundle, output)
    elif kind in ("bkt", "logistic"):
        module = baselines
        owner = baselines.BKTBaseline if kind == "bkt" else baselines.LogisticBaseline
        method = "fit"
        run = lambda output: module.train_baseline(bundle, output, model_kind=kind)
    elif kind == "dkt":
        module, owner, method = dkt, dkt, "_fit"
        config = dkt.DKTTrainingConfig(max_epochs=1, patience=1, batch_size=8)
        run = lambda output: module.train_dkt(bundle, output, config=config)
    else:
        base_run = tmp_path / "base"
        rates.train_rates(bundle, base_run)
        module, owner, method = calibration, calibration.TemperatureScaler, "fit_validation"
        run = lambda output: module.calibrate_baseline(bundle, base_run / "model.json", output)

    original = getattr(owner, method)

    def mutate_then_fit(*args, **kwargs):
        change_manifest_version(bundle)
        return original(*args, **kwargs)

    monkeypatch.setattr(owner, method, mutate_then_fit)
    output = tmp_path / "rejected-run"
    with pytest.raises(ValueError, match="Processing manifest changed during"):
        run(output)
    assert not output.exists()
    assert sha256((bundle / "manifest.json").read_bytes()).hexdigest() != initial_hash
