import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from practice_engine.data.manifest import ProcessingManifest, verify_manifest

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"


def process(output, *flags):
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE),
                    "--output", str(output), *flags], check=True, capture_output=True)


def test_manifest_reproduces_versions_and_hashes(tmp_path):
    tmp_path = tmp_path / "bundle"
    process(tmp_path, "--synthetic", "--dataset-version", "synthetic-v1")
    first = verify_manifest(tmp_path / "manifest.json")
    assert first.source_kind == "synthetic" and first.dataset_version == "synthetic-v1"
    assert first.trained_model_version is None and first.release_verified is False
    split = json.loads((tmp_path / "split.json").read_text())
    assert first.source_sha256 == split["source_sha256"] and first.seed == split["seed"]
    process(tmp_path.parent / "repeat", "--synthetic", "--dataset-version", "synthetic-v1")
    assert first == verify_manifest(tmp_path.parent / "repeat" / "manifest.json")
    assert first == verify_manifest(tmp_path / "manifest.json")


def test_unknown_source_not_silently_labeled_synthetic(tmp_path):
    tmp_path = tmp_path / "bundle"
    process(tmp_path)
    manifest = verify_manifest(tmp_path / "manifest.json")
    assert manifest.source_kind == "unverified"
    assert manifest.redistribution_terms_verified is False


def test_tampering_and_path_injection_rejected(tmp_path):
    tmp_path = tmp_path / "bundle"
    process(tmp_path)
    path = tmp_path / "manifest.json"
    (tmp_path / "train.jsonl").write_text("modified\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_manifest(path)
    data = json.loads(path.read_text())
    data["artifact_sha256"]["../private"] = "a" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="exactly"):
        verify_manifest(path)


def test_cannot_claim_verified_terms_or_empty_version():
    kwargs = dict(dataset_version="v1", source_kind="unverified", source_sha256="a" * 64, seed=38)
    for changes in ({"release_verified": True}, {"redistribution_terms_verified": True}, {"dataset_version": " "}):
        with pytest.raises(ValidationError):
            ProcessingManifest(**{**kwargs, **changes})
