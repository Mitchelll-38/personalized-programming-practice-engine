import json
from pathlib import Path
import subprocess
import sys

import pytest

from practice_engine.data.manifest import artifact_hashes
from practice_engine.models.artifacts import load_rate_artifact
from practice_engine.training.rates import train_rates

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"


@pytest.fixture
def bundle(tmp_path):
    path = tmp_path / "bundle"
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE), "--output", str(path),
                    "--synthetic", "--dataset-version", "synthetic-v1"], check=True, capture_output=True)
    return path


def refresh_hashes(bundle):
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    path.write_text(json.dumps(manifest))


def test_training_records_validation_only_and_deterministic_model(bundle, tmp_path):
    first = train_rates(bundle, tmp_path / "run-one")
    second = train_rates(bundle, tmp_path / "run-two")
    assert first == second
    assert first["test_evaluated"] is False and first["research_results"] is False
    assert first["train_examples"] == 8 and first["validation_examples"] == 2
    assert load_rate_artifact(tmp_path / "run-one/model.json") == load_rate_artifact(tmp_path / "run-two/model.json")
    assert json.loads((tmp_path / "run-one/validation.json").read_text())["aggregate"]["n_examples"] == 2
    with pytest.raises(ValueError, match="new directory"):
        train_rates(bundle, tmp_path / "run-one")


def test_test_labels_are_not_parsed_or_used(bundle, tmp_path):
    # Integrity hashes cover test bytes, but training never parses test examples.
    (bundle / "test.jsonl").write_text("deliberately invalid JSON\n")
    refresh_hashes(bundle)
    assert train_rates(bundle, tmp_path / "run")["test_evaluated"] is False


def test_integrity_and_provenance_fail_before_run_write(bundle, tmp_path):
    path = bundle / "manifest.json"
    data = json.loads(path.read_text())
    data["source_kind"] = "unverified"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="synthetic"):
        train_rates(bundle, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_wrong_partition_membership_rejected_before_fit(bundle, tmp_path):
    path = bundle / "train.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["student_id"] = "validation-student"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    refresh_hashes(bundle)
    with pytest.raises(ValueError, match="student partition"):
        train_rates(bundle, tmp_path / "run")
    assert not (tmp_path / "run").exists()
