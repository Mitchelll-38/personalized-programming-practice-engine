"""Synthetic processing publication must preserve destination integrity."""

from pathlib import Path
import subprocess
import sys

import pytest

from practice_engine.data import cli
from practice_engine.data.manifest import verify_manifest
from practice_engine.training.bundle import load_training_bundle

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"


def invoke(monkeypatch, output):
    monkeypatch.setattr(sys, "argv", ["practice-data", str(FIXTURE), "--synthetic", "--output", str(output)])
    cli.main()


def test_real_cli_publishes_complete_loadable_bundle(tmp_path):
    output = tmp_path / "nested" / "bundle"
    result = subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE),
        "--synthetic", "--output", str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert verify_manifest(output / "manifest.json").source_kind == "synthetic"
    assert len(load_training_bundle(output).validation) == 2
    assert set(p.name for p in output.iterdir()) == {
        "audit.json", "split.json", "train.jsonl", "validation.jsonl", "test.jsonl", "manifest.json"}
    assert list(output.parent.iterdir()) == [output]


@pytest.mark.parametrize("kind", ["directory", "file", "broken-symlink"])
def test_existing_output_is_never_changed(tmp_path, monkeypatch, kind):
    output = tmp_path / "bundle"
    if kind == "directory":
        output.mkdir()
        (output / "keep").write_bytes(b"existing")
    elif kind == "file":
        output.write_bytes(b"existing")
    else:
        try:
            output.symlink_to(tmp_path / "missing", target_is_directory=True)
        except OSError:
            pytest.skip("Host does not permit creation of directory symlinks")
    with pytest.raises(ValueError, match="new directory"):
        invoke(monkeypatch, output)
    if kind == "directory":
        assert (output / "keep").read_bytes() == b"existing"
    elif kind == "file":
        assert output.read_bytes() == b"existing"
    else:
        assert output.is_symlink() and not output.exists()
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("failure", ["split.json", "manifest.json", "rename"])
def test_write_and_publish_failures_leave_no_partial_bundle(tmp_path, monkeypatch, failure):
    output = tmp_path / "bundle"
    original_write = Path.write_text
    def write(path, *args, **kwargs):
        assert not output.exists()
        if path.name == failure:
            raise OSError("injected write failure")
        return original_write(path, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", write)
    if failure == "rename":
        def rename(*args):
            raise OSError("injected publish failure")
        monkeypatch.setattr(cli.os, "rename", rename)
    with pytest.raises(OSError, match="injected"):
        invoke(monkeypatch, output)
    assert not output.exists() and list(tmp_path.iterdir()) == []


def test_destination_appearing_during_staging_is_preserved(tmp_path, monkeypatch):
    output = tmp_path / "bundle"
    original = cli.write_manifest
    def manifest(*args):
        original(*args)
        output.mkdir()
        (output / "keep").write_bytes(b"other writer")
    monkeypatch.setattr(cli, "write_manifest", manifest)
    with pytest.raises(ValueError, match="new directory"):
        invoke(monkeypatch, output)
    assert (output / "keep").read_bytes() == b"other writer"
    assert list(tmp_path.iterdir()) == [output]


def test_other_cli_publish_lock_is_preserved(tmp_path, monkeypatch):
    output = tmp_path / "bundle"
    lock = tmp_path / ".bundle.publish-lock"
    lock.mkdir()
    with pytest.raises(FileExistsError):
        invoke(monkeypatch, output)
    assert list(tmp_path.iterdir()) == [lock]
