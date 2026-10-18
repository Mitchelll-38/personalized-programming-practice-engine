from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.manifest import artifact_hashes
from practice_engine.models.artifacts import payload_hash
from practice_engine.models.codebert import CACHE_NAMESPACE, codebert_config, query_contents
from practice_engine.models.embedding_cache import cache_key, save_embedding
from practice_engine.models.serving import PredictionInput
from practice_engine.training import content_run
from practice_engine.training.bundle import load_training_bundle
from practice_engine.training.content import ContentTrainingConfig

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    bundle, cache = tmp_path / "bundle", tmp_path / "cache"
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE),
        "--synthetic", "--output", str(bundle)], capture_output=True, check=True)
    verified = load_training_bundle(bundle)
    encoder = codebert_config(max_tokens=16)
    for row in [*verified.train, *verified.validation]:
        for item in query_contents(PredictionInput.model_validate(row.model_dump(exclude={"label"}))):
            key = cache_key(item.text, item.role, encoder)
            path = cache / "embeddings" / CACHE_NAMESPACE / f"{key}.json"
            if not path.exists():
                save_embedding(path, item.text, item.role, encoder, [len(item.text) / 100] * encoder.dimension)
    monkeypatch.setattr("practice_engine.training.content_cache.FrozenCodeBERT",
                        lambda *a, **k: pytest.fail("run initialized an encoder"))
    return bundle, cache, encoder


def config():
    return ContentTrainingConfig(max_epochs=2, patience=1, batch_size=3, projection_size=4,
                                 concept_size=3, correctness_size=2, hidden_size=5)


def run(prepared, output):
    bundle, cache, encoder = prepared
    return content_run.train_content(bundle, cache, output, encoder=encoder, config=config())


def refresh(bundle):
    path = bundle / "manifest.json"
    payload = json.loads(path.read_text())
    payload["artifact_sha256"] = artifact_hashes(bundle)
    path.write_text(json.dumps(payload))


def test_repeatable_run_hashes_counts_parity_and_private_aggregate_metadata(prepared, tmp_path):
    first = run(prepared, tmp_path / "first")
    second = run(prepared, tmp_path / "second")
    assert first == second
    assert first["reload_predictions_equal"] and not first["test_evaluated"] and not first["test_examples_read"]
    assert first["train_examples"] == 8 and first["validation_examples"] == 2 and first["embedding_entries"] == 3
    assert first["config_sha256"] == payload_hash(first["config"])
    assert first["encoder_sha256"] == payload_hash(first["encoder"])
    bundle, cache, encoder = prepared
    verified = load_training_bundle(bundle)
    entries = content_run.load_content_entries([*verified.train, *verified.validation], cache, encoder)
    assert first["embedding_inventory_sha256"] == payload_hash({"cache_namespace": CACHE_NAMESPACE,
        "encoder": encoder.model_dump(), "entries": {key: entries[key].entry_sha256 for key in sorted(entries)}})
    assert first["processing_manifest_sha256"] == sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    assert (tmp_path / "first/validation.json").read_bytes() == (tmp_path / "second/validation.json").read_bytes()
    metrics = json.loads((tmp_path / "first/validation.json").read_text())
    assert "per_student" not in metrics and "equal_student_macro" in metrics
    assert all(row.student_id not in json.dumps(metrics) for row in verified.validation)
    serialized = json.dumps(first)
    assert all(key not in serialized for key in ('"student_id"', '"problem_id"', '"label"', '"submitted_code"'))
    assert not list(tmp_path.glob(".first.*"))


def test_binary_test_examples_never_parsed(prepared, tmp_path):
    original = run(prepared, tmp_path / "first")
    (prepared[0] / "test.jsonl").write_bytes(b"\x00\xffnot canonical JSON")
    refresh(prepared[0])
    changed = run(prepared, tmp_path / "second")
    assert changed["epochs"] == original["epochs"]
    assert changed["checkpoint_weights_sha256"] == original["checkpoint_weights_sha256"]
    assert changed["test_examples_read"] is False


def test_evaluator_extensions_cannot_add_row_or_learner_outputs(prepared, tmp_path, monkeypatch):
    original = content_run.evaluate
    def extended(*args):
        return {**original(*args), "future_rows": [{"student_id": "private", "score": .2}],
                "future_learners": {"private": {"label": True}}}
    monkeypatch.setattr(content_run, "evaluate", extended)
    run(prepared, tmp_path / "run")
    payload = json.loads((tmp_path / "run/validation.json").read_text())
    assert set(payload) == {"aggregate", "equal_student_macro", "metric_definitions"}
    assert "private" not in json.dumps(payload)


@pytest.mark.parametrize("fail_replay", [False, True])
def test_default_sized_replay_scopes_threads_and_determinism(prepared, tmp_path, monkeypatch, fail_replay):
    bundle, cache, encoder = prepared
    first = json.loads((bundle / "validation.jsonl").read_text().splitlines()[0])
    rows = []
    for index in range(32):
        row = {**first, "target_sequence_index": 100 + index,
               "candidate": {**first["candidate"], "problem_id": f"heldout-{index}"}}
        rows.append(json.dumps(row))
    (bundle / "validation.jsonl").write_text("\n".join(rows) + "\n")
    refresh(bundle)
    original = content_run.load_content_checkpoint
    observed_batches = []
    def checked(path):
        checkpoint = original(path)
        class Checked:
            def logits(self, inputs):
                assert torch.get_num_threads() == 1 and torch.are_deterministic_algorithms_enabled()
                observed_batches.append(len(inputs.lengths))
                if fail_replay:
                    raise ValueError("injected replay failure")
                return checkpoint.logits(inputs)
        return Checked()
    monkeypatch.setattr(content_run, "load_content_checkpoint", checked)
    threads, enabled, warn = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled(), torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(False, warn_only=True)
        if fail_replay:
            with pytest.raises(ValueError, match="injected replay"):
                content_run.train_content(bundle, cache, tmp_path / "run", encoder=encoder,
                    config=ContentTrainingConfig(max_epochs=1))
            assert not (tmp_path / "run").exists() and not list(tmp_path.glob(".run.*"))
        else:
            result = content_run.train_content(bundle, cache, tmp_path / "run", encoder=encoder,
                config=ContentTrainingConfig(max_epochs=1))
            assert result["reload_predictions_equal"] and result["validation_examples"] == 32
        assert observed_batches == [32]
        assert torch.get_num_threads() == 2 and not torch.are_deterministic_algorithms_enabled()
        assert torch.is_deterministic_algorithms_warn_only_enabled()
    finally:
        torch.use_deterministic_algorithms(enabled, warn_only=warn)
        torch.set_num_threads(threads)


@pytest.mark.parametrize("fault", ["unverified", "corrupt", "missing-cache", "modified-cache"])
def test_source_gate_and_cache_integrity_fail_without_publication(prepared, tmp_path, monkeypatch, fault):
    bundle, cache, _ = prepared
    if fault == "unverified":
        payload = json.loads((bundle / "manifest.json").read_text())
        payload["source_kind"] = "unverified"
        (bundle / "manifest.json").write_text(json.dumps(payload))
        monkeypatch.setattr(content_run, "load_content_entries", lambda *a: pytest.fail("cache read before source gate"))
    elif fault == "corrupt":
        (bundle / "train.jsonl").write_text("corrupt")
    else:
        path = next((cache / "embeddings" / CACHE_NAMESPACE).glob("*.json"))
        if fault == "missing-cache":
            path.unlink()
        else:
            payload = json.loads(path.read_text())
            payload["vector"][0] += 1
            path.write_text(json.dumps(payload))
    with pytest.raises((ValueError, FileNotFoundError)):
        run(prepared, tmp_path / "run")
    assert not (tmp_path / "run").exists() and not list(tmp_path.glob(".run.*"))


@pytest.mark.parametrize("fault", ["checkpoint", "parity", "manifest"])
def test_failure_cleans_owned_staging_and_lock(prepared, tmp_path, monkeypatch, fault):
    if fault == "checkpoint":
        def fail(*args):
            raise OSError("injected checkpoint failure")
        monkeypatch.setattr(content_run, "save_content_checkpoint", fail)
    elif fault == "parity":
        class Wrong:
            def logits(self, inputs):
                return torch.full((len(inputs.lengths),), -999.)
        monkeypatch.setattr(content_run, "load_content_checkpoint", lambda *a: Wrong())
    else:
        original = content_run.fit_content
        def changed(*args, **kwargs):
            fit = original(*args, **kwargs)
            path = prepared[0] / "manifest.json"
            path.write_bytes(path.read_bytes() + b" ")
            return fit
        monkeypatch.setattr(content_run, "fit_content", changed)
    with pytest.raises((ValueError, OSError)):
        run(prepared, tmp_path / "run")
    assert not (tmp_path / "run").exists() and not list(tmp_path.glob(".run.*"))


def test_no_clobber_existing_run_or_competing_lock(prepared, tmp_path):
    run(prepared, tmp_path / "run")
    before = (tmp_path / "run/run.json").read_bytes()
    with pytest.raises(FileExistsError):
        run(prepared, tmp_path / "run")
    assert before == (tmp_path / "run/run.json").read_bytes()
    lock = tmp_path / ".other.publish-lock"
    lock.mkdir()
    with pytest.raises(FileExistsError):
        run(prepared, tmp_path / "other")
    assert lock.is_dir() and not (tmp_path / "other").exists()


def test_cli_and_ambient_default_device(prepared, tmp_path, monkeypatch, capsys):
    bundle, cache, _ = prepared
    monkeypatch.setattr(sys, "argv", ["content-run", str(bundle), "--encoder-directory", str(cache),
        "--output", str(tmp_path / "run"), "--max-tokens", "16", "--max-epochs", "1",
        "--projection-size", "4", "--concept-size", "3", "--correctness-size", "2", "--hidden-size", "5"])
    with torch.device("meta"):
        content_run.main()
        assert torch.empty(0).device.type == "meta"
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["encoder"]["max_tokens"] == 16 and receipt["epochs_completed"] == 1
    assert receipt["reload_predictions_equal"]
