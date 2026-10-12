from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from practice_engine.data.manifest import verify_manifest

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/codeworkout"


def run_cli(output, *flags):
    return subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE),
                           "--output", str(output), *flags], capture_output=True, text=True)


def test_import_cli_audits_sources_and_reuses_causal_processing(tmp_path):
    command = ("--format", "codeworkout", "--catalog", str(FIXTURE / "catalog.json"),
               "--synthetic", "--dataset-version", "codeworkout-synthetic-v1")
    result = run_cli(tmp_path, *command)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "audit.json").read_text())
    assert (report["interactions"], report["first_attempts"], report["retries_excluded"]) == (6, 5, 1)
    assert report["import"]["non_submission_events_excluded"] == 2
    assert report["import"]["source_sha256"]["MainTable.csv"] == sha256((FIXTURE / "MainTable.csv").read_bytes()).hexdigest()
    assert "Run.Program" in report["label_definition"]
    manifest = verify_manifest(tmp_path / "manifest.json")
    assert manifest.source_kind == "synthetic" and manifest.dataset_version == "codeworkout-synthetic-v1"
    examples = [json.loads(line) for group in ("train", "validation", "test")
                for line in (tmp_path / f"{group}.jsonl").read_text().splitlines()]
    assert len(examples) == 5
    assert all("submitted_code" not in example["candidate"] for example in examples)
    assert run_cli(tmp_path, *command).returncode == 0
    assert manifest == verify_manifest(tmp_path / "manifest.json")


def test_invalid_catalog_arguments_write_no_artifacts(tmp_path):
    missing = tmp_path / "missing"
    result = run_cli(missing, "--format", "codeworkout")
    assert result.returncode != 0 and "--catalog is required" in result.stderr
    assert not missing.exists()
    result = run_cli(missing, "--catalog", str(FIXTURE / "catalog.json"))
    assert result.returncode != 0 and "only valid" in result.stderr
    assert not missing.exists()
