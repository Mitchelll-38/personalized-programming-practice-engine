import json
from pathlib import Path
import subprocess
import sys

import pytest

from practice_engine.data.manifest import artifact_hashes
from practice_engine.models.codebert import CACHE_NAMESPACE, codebert_config, query_contents
from practice_engine.models.embedding_cache import cache_key, save_embedding
from practice_engine.training import content_cache
from practice_engine.training.bundle import load_training_bundle

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"


@pytest.fixture
def bundle(tmp_path):
    path = tmp_path / "bundle"
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE),
        "--synthetic", "--output", str(path)], check=True, capture_output=True)
    return path


@pytest.fixture
def backend(monkeypatch):
    calls = []
    class Encoder:
        def __init__(self, directory, *, config, allow_download):
            self.directory, self.config = directory, config
            assert allow_download is False
        def encode(self, query):
            assert not hasattr(query, "label")
            calls.append(query)
            for item in query_contents(query):
                key = cache_key(item.text, item.role, self.config)
                path = self.directory / "embeddings" / CACHE_NAMESPACE / f"{key}.json"
                if not path.exists():
                    save_embedding(path, item.text, item.role, self.config, [.25] * self.config.dimension)
    monkeypatch.setattr(content_cache, "FrozenCodeBERT", Encoder)
    return calls


def test_receipt_is_repeatable_private_and_covers_only_verified_train_validation(bundle, tmp_path, backend):
    directory = tmp_path / "private-encoder"
    verified = load_training_bundle(bundle)
    config = codebert_config(max_tokens=16)
    receipt = content_cache.prepare_content_cache(bundle, directory, config=config)
    assert len(backend) == len(verified.train) + len(verified.validation)
    assert receipt["train_examples"] == 8 and receipt["validation_examples"] == 2
    assert receipt["test_examples_read"] is False and receipt["research_results"] is False
    assert receipt["provenance"] == verified.provenance.model_dump()
    assert receipt["encoder"] == config.model_dump()
    entries = content_cache.load_content_entries([*verified.train, *verified.validation], directory, config)
    assert receipt["entries"] == {key: entry.entry_sha256 for key, entry in sorted(entries.items())}
    assert all(key not in json.dumps(receipt) for key in ('"student_id"', '"problem_id"', '"correct"', '"label"'))
    assert content_cache.prepare_content_cache(bundle, directory, config=config) == receipt
    assert len(list((directory / "embeddings" / CACHE_NAMESPACE).glob("*.json"))) == len(entries)


def test_binary_test_poison_is_hashed_never_parsed(bundle, tmp_path, backend):
    (bundle / "test.jsonl").write_bytes(b"\x00\xffnot JSON, never a feature input")
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    receipt = content_cache.prepare_content_cache(bundle, tmp_path / "encoder")
    assert receipt["test_examples_read"] is False and len(backend) == 10


@pytest.mark.parametrize("failure", ["unverified", "corrupt", "future"])
def test_bad_bundle_fails_before_encoder_initialization(bundle, tmp_path, monkeypatch, failure):
    if failure == "unverified":
        value = json.loads((bundle / "manifest.json").read_text())
        value["source_kind"] = "unverified"
        (bundle / "manifest.json").write_text(json.dumps(value))
    else:
        if failure == "future":
            rows = [json.loads(line) for line in (bundle / "train.jsonl").read_text().splitlines()]
            row = rows[0]
            row["history"] = [{**row["candidate"], "student_id": row["student_id"],
                "sequence_index": row["target_sequence_index"], "correct": False, "attempt_number": 1}]
            (bundle / "train.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            value = json.loads((bundle / "manifest.json").read_text())
            value["artifact_sha256"] = artifact_hashes(bundle)
            (bundle / "manifest.json").write_text(json.dumps(value))
        else:
            (bundle / "train.jsonl").write_text("not canonical JSON\n")
    monkeypatch.setattr(content_cache, "FrozenCodeBERT", lambda *a, **k: pytest.fail("encoder initialized before gate"))
    with pytest.raises(ValueError):
        content_cache.prepare_content_cache(bundle, tmp_path / "encoder")
    assert not (tmp_path / "encoder").exists()


def test_offline_loader_rejects_missing_modified_or_wrong_config_without_encoder(bundle, tmp_path, backend, monkeypatch):
    config = codebert_config(max_tokens=8)
    directory = tmp_path / "encoder"
    content_cache.prepare_content_cache(bundle, directory, config=config)
    rows = load_training_bundle(bundle).train
    monkeypatch.setattr(content_cache, "FrozenCodeBERT", lambda *a, **k: pytest.fail("offline loader initialized encoder"))
    assert content_cache.load_content_entries(rows, directory, config)
    with pytest.raises(FileNotFoundError):
        content_cache.load_content_entries(rows, directory, codebert_config(max_tokens=9))
    path = next((directory / "embeddings" / CACHE_NAMESPACE).glob("*.json"))
    value = json.loads(path.read_text())
    value["vector"][0] = 9.
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        content_cache.load_content_entries([*rows, *load_training_bundle(bundle).validation], directory, config)


def test_changed_manifest_during_encoding_returns_no_receipt(bundle, tmp_path, backend, monkeypatch):
    original = content_cache.FrozenCodeBERT.encode
    def changed(self, query):
        original(self, query)
        path = bundle / "manifest.json"
        path.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr(content_cache.FrozenCodeBERT, "encode", changed)
    with pytest.raises(ValueError, match="manifest changed"):
        content_cache.prepare_content_cache(bundle, tmp_path / "encoder")


def test_cli_options_and_lazy_imports(bundle, tmp_path, backend, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["content-cache", str(bundle), "--encoder-directory", str(tmp_path / "encoder"),
        "--max-tokens", "16", "--pooling", "cls", "--truncation", "left"])
    content_cache.main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["encoder"]["pooling"] == "cls" and receipt["encoder"]["max_tokens"] == 16
    subprocess.run([sys.executable, "-c", "import sys; import practice_engine.training.content_cache; "
        "assert not {'torch','transformers','huggingface_hub'}.intersection(sys.modules)"], check=True)
