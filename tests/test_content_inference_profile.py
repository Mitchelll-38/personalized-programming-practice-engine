from hashlib import sha256
import json

import pytest

torch = pytest.importorskip("torch")

from practice_engine import content_inference_profile as profiler
from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, payload_hash
from practice_engine.models.codebert import CACHE_NAMESPACE
from practice_engine.models.content_artifacts import save_content_checkpoint
from practice_engine.models.content_inputs import ConceptVocabulary
from practice_engine.models.content_lstm import ContentLSTM
from practice_engine.models.embedding_cache import EncoderConfig, cache_key, save_embedding


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    encoder = EncoderConfig(repository="synthetic/encoder", revision="a" * 40,
        tokenizer="synthetic/tokenizer", tokenizer_revision="b" * 40, pooling="mean",
        max_tokens=16, truncation="right", dimension=3)
    row = PredictionExample(student_id="synthetic-private", target_sequence_index=0, history=(), label=True,
        candidate=Candidate(problem_id="private-problem", problem_text="Original synthetic text", concept_ids=("loops",)))
    vocabulary = ConceptVocabulary.fit([row])
    with torch.random.fork_rng(devices=[]):
        model = ContentLSTM(vocabulary.size, input_size=3, projection_size=4,
                            concept_size=3, correctness_size=2, hidden_size=5)
    provenance = ArtifactProvenance(dataset_version="synthetic-profile-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="synthetic-split-v1", split_sha256="b" * 64)
    model_path, query_path, cache = tmp_path / "model", tmp_path / "queries.json", tmp_path / "cache"
    metadata = save_content_checkpoint(model_path, model, vocabulary, encoder, provenance)
    query_path.write_text(json.dumps({"inputs": [row.model_dump(exclude={"label"})]}))
    key = cache_key(row.candidate.problem_text, "problem-text", encoder)
    entry_path = cache / "embeddings" / CACHE_NAMESPACE / f"{key}.json"
    entry = save_embedding(entry_path, row.candidate.problem_text, "problem-text", encoder, [1., 2., 3.])
    monkeypatch.setattr("practice_engine.training.content_cache.FrozenCodeBERT",
                        lambda *a, **k: pytest.fail("profiler initialized encoder"))
    return model_path, query_path, cache, metadata, entry, entry_path


def test_exact_identities_timing_scope_call_counts_and_no_private_outputs(prepared, monkeypatch):
    model, queries, cache, metadata, entry, _ = prepared
    calls = []
    original = profiler.predict_content_inputs
    def tracked(*args, **kwargs):
        calls.append(kwargs)
        assert torch.get_num_threads() == 1 and torch.are_deterministic_algorithms_enabled()
        return original(*args, **kwargs)
    monkeypatch.setattr(profiler, "predict_content_inputs", tracked)
    ticks = iter(range(0, 140, 10))
    monkeypatch.setattr(profiler, "perf_counter_ns", lambda: next(ticks))
    before = queries.read_bytes()
    result = profiler.profile_content_inference(model, queries, cache, repeats=3, warmups=2, batch_size=1)
    assert calls == [{"batch_size": 1}] * 5
    assert result["checkpoint_metadata_sha256"] == metadata.metadata_sha256
    assert result["checkpoint_weights_sha256"] == metadata.weights_sha256
    assert result["queries_sha256"] == sha256(before).hexdigest() and queries.read_bytes() == before
    assert result["encoder_sha256"] == payload_hash(metadata.encoder.model_dump())
    assert result["embedding_inventory_sha256"] == payload_hash({"cache_namespace": CACHE_NAMESPACE,
        "encoder": metadata.encoder.model_dump(), "entries": {entry.key_sha256: entry.entry_sha256}})
    assert result["batch_ms"] == {key: .00001 for key in ("min", "median", "p95", "max")}
    assert all(result[key] == .00001 for key in ("checkpoint_load_ms", "query_parse_ms", "cache_load_ms", "warmup_ms"))
    assert result["queries_per_second"] == 100_000_000.
    serialized = json.dumps(result)
    assert all(value not in serialized for value in ("synthetic-private", "private-problem", "Original synthetic text"))
    assert result["labels_evaluated"] is False and result["encoder_initialized"] is False and result["network_used"] is False


@pytest.mark.parametrize("change", [{"repeats": True}, {"repeats": 0}, {"repeats": 101},
    {"warmups": -1}, {"warmups": 11}, {"batch_size": 0}, {"batch_size": 257}])
def test_invalid_configuration_fails_before_files(change):
    with pytest.raises(ValueError):
        profiler.profile_content_inference("absent", "absent", "absent", **change)


@pytest.mark.parametrize("fault", ["label", "target-code", "future", "empty", "too-many", "history", "bytes", "duplicate"])
def test_query_gates_fail_before_cache_or_prediction(prepared, monkeypatch, fault):
    model, queries, cache, *_ = prepared
    payload = json.loads(queries.read_text())
    row = payload["inputs"][0]
    if fault == "label": row["label"] = True
    elif fault == "target-code": row["candidate"]["submitted_code"] = "poison"
    elif fault == "future": row["history"] = [{**row["candidate"], "student_id": row["student_id"],
        "sequence_index": 0, "correct": False, "attempt_number": 1}]
    elif fault == "empty": payload["inputs"] = []
    elif fault == "too-many": payload["inputs"] *= 257
    elif fault == "history": row["history"] = [{}] * 257
    queries.write_text(json.dumps(payload))
    if fault == "bytes": queries.write_bytes(b" " * (8 * 1024 * 1024 + 1))
    if fault == "duplicate": queries.write_text('{"inputs": [], "inputs": []}')
    monkeypatch.setattr(profiler, "load_content_entries", lambda *a: pytest.fail("bad query reached cache"))
    with pytest.raises(ValueError):
        profiler.profile_content_inference(model, queries, cache)


@pytest.mark.parametrize("fault", ["source", "weights", "entry"])
def test_integrity_and_source_gates(prepared, monkeypatch, fault):
    model, queries, cache, _, _, entry_path = prepared
    if fault == "weights":
        (model / "weights.pt").write_bytes((model / "weights.pt").read_bytes() + b"corrupt")
    elif fault == "entry":
        payload = json.loads(entry_path.read_text())
        payload["vector"][0] = 99.
        entry_path.write_text(json.dumps(payload))
    else:
        payload = json.loads((model / "metadata.json").read_text())
        payload["provenance"]["source_kind"] = "unverified"
        payload["metadata_sha256"] = payload_hash({key: value for key, value in payload.items() if key != "metadata_sha256"})
        (model / "metadata.json").write_text(json.dumps(payload))
        monkeypatch.setattr(profiler, "load_content_entries", lambda *a: pytest.fail("unverified source reached cache"))
    with pytest.raises(ValueError):
        profiler.profile_content_inference(model, queries, cache)


def test_mutated_live_checkpoint_is_rejected_after_warmup(prepared, monkeypatch):
    model, queries, cache, *_ = prepared
    original = profiler.predict_content_inputs
    def mutate(checkpoint, *args, **kwargs):
        scores = original(checkpoint, *args, **kwargs)
        with torch.no_grad():
            checkpoint._model.head.bias.add_(1)
        return scores
    monkeypatch.setattr(profiler, "predict_content_inputs", mutate)
    with pytest.raises(ValueError, match="changed"):
        profiler.profile_content_inference(model, queries, cache, repeats=1, warmups=1)


@pytest.mark.parametrize("failure", [False, True])
def test_caller_settings_and_rng_restored_including_failure(prepared, monkeypatch, failure):
    model, queries, cache, *_ = prepared
    threads, enabled, warn = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled(), torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(False, warn_only=True)
        rng = torch.get_rng_state().clone()
        if failure:
            def fail(*args, **kwargs):
                torch.rand(1)
                raise ValueError("injected profile failure")
            monkeypatch.setattr(profiler, "predict_content_inputs", fail)
        with torch.device("meta"):
            if failure:
                with pytest.raises(ValueError, match="injected"):
                    profiler.profile_content_inference(model, queries, cache, repeats=1, warmups=0)
            else:
                profiler.profile_content_inference(model, queries, cache, repeats=1, warmups=0)
            assert torch.empty(0).device.type == "meta"
        assert torch.equal(rng, torch.get_rng_state()) and torch.get_num_threads() == 2
        assert not torch.are_deterministic_algorithms_enabled() and torch.is_deterministic_algorithms_warn_only_enabled()
    finally:
        torch.use_deterministic_algorithms(enabled, warn_only=warn)
        torch.set_num_threads(threads)


def test_cli(prepared, monkeypatch, capsys):
    model, queries, cache, *_ = prepared
    monkeypatch.setattr("sys.argv", ["content-profile", str(model), str(queries), "--encoder-directory", str(cache),
        "--warmups", "0", "--repeats", "1", "--batch-size", "1"])
    profiler.main()
    assert json.loads(capsys.readouterr().out)["repeats"] == 1
