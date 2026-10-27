from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from practice_engine.data import cli
from practice_engine.data.manifest import verify_manifest

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/codeworkout"


def run_cli(output, *flags):
    return subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE),
                           "--output", str(output), *flags], capture_output=True, text=True)


def test_import_cli_audits_sources_and_reuses_causal_processing(tmp_path):
    tmp_path = tmp_path / "bundle"
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
    assert run_cli(tmp_path, *command).returncode != 0
    assert manifest == verify_manifest(tmp_path / "manifest.json")


def test_invalid_catalog_arguments_write_no_artifacts(tmp_path):
    missing = tmp_path / "missing"
    result = run_cli(missing, "--format", "codeworkout")
    assert result.returncode != 0 and "--catalog is required" in result.stderr
    assert not missing.exists()
    result = run_cli(missing, "--catalog", str(FIXTURE / "catalog.json"))
    assert result.returncode != 0 and "only valid" in result.stderr
    assert not missing.exists()


@pytest.mark.parametrize("change", ["score", "remove-optional-code-table"])
def test_source_change_after_import_cannot_publish_mismatched_receipt(tmp_path, monkeypatch, change):
    release = tmp_path / "release"
    shutil.copytree(FIXTURE, release)
    output = tmp_path / "bundle"
    original_import = cli.import_codeworkout

    def import_then_change(directory, catalog):
        imported = original_import(directory, catalog)
        if change == "score":
            table = directory / "MainTable.csv"
            table.write_text(table.read_text().replace(
                "e6,synthetic-b,1,1,2026-01-01T12:00:00Z,Run.Program,0,,99",
                "e6,synthetic-b,1,1,2026-01-01T12:00:00Z,Run.Program,1,,99"))
        else:
            (directory / "CodeStates/CodeStates.csv").unlink()
        return imported

    monkeypatch.setattr(cli, "import_codeworkout", import_then_change)
    monkeypatch.setattr(sys, "argv", ["practice-data", str(release), "--format", "codeworkout",
        "--catalog", str(release / "catalog.json"), "--synthetic", "--output", str(output)])
    with pytest.raises(ValueError, match="source files changed"):
        cli.main()
    assert not output.exists() and not (output / "manifest.json").exists()


def test_source_change_during_staging_cleans_unpublished_bundle(tmp_path, monkeypatch):
    release = tmp_path / "release"
    shutil.copytree(FIXTURE, release)
    output = tmp_path / "bundle"
    original_write = cli.write_manifest

    def write_then_change(directory, manifest):
        original_write(directory, manifest)
        catalog = release / "catalog.json"
        catalog.write_text(catalog.read_text() + "\n")

    monkeypatch.setattr(cli, "write_manifest", write_then_change)
    monkeypatch.setattr(sys, "argv", ["practice-data", str(release), "--format", "codeworkout",
        "--catalog", str(release / "catalog.json"), "--synthetic", "--output", str(output)])
    with pytest.raises(ValueError, match="source files changed"):
        cli.main()
    assert not output.exists() and not list(tmp_path.glob(".bundle*"))
