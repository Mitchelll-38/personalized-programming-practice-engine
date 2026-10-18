import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from practice_engine.models.artifacts import payload_hash
from practice_engine.models.embedding_cache import EncoderConfig, cache_key, load_embedding, make_entry, save_embedding


@pytest.fixture
def config():
    return EncoderConfig(repository="synthetic/declared-encoder", revision="a" * 40,
                         tokenizer="synthetic/declared-tokenizer", tokenizer_revision="b" * 40,
                         pooling="mean", max_tokens=32, truncation="right", dimension=3)


def test_exact_utf8_content_role_and_every_encoder_field_changes_key(config):
    original = cache_key("Synthetic π exercise", "problem-text", config)
    assert original == cache_key("Synthetic π exercise", "problem-text", config)
    assert original != cache_key("Synthetic π exercise ", "problem-text", config)
    assert original != cache_key("Synthetic π exercise", "historical-code", config)
    for field, value in {"repository": "synthetic/other", "revision": "c" * 40,
                         "tokenizer": "synthetic/other-tokenizer", "tokenizer_revision": "d" * 40,
                         "pooling": "cls", "max_tokens": 64, "truncation": "left", "dimension": 4}.items():
        changed = EncoderConfig.model_validate({**config.model_dump(), field: value})
        assert original != cache_key("Synthetic π exercise", "problem-text", changed)
    assert cache_key("é", "problem-text", config) != cache_key("e\u0301", "problem-text", config)


def test_round_trip_is_detached_immutable_and_persists_no_input_text(tmp_path, config):
    text = "Original synthetic submitted code: return 17;"
    values = [1., .25, -2.]
    path = tmp_path / "entry.json"
    entry = save_embedding(path, text, "historical-code", config, values)
    values[0] = 99.
    payload = entry.to_dict()
    payload["vector"][0] = 77.
    payload["encoder"]["repository"] = "changed"
    assert entry.vector == (1., .25, -2.)
    assert load_embedding(path, text, "historical-code", config) == entry
    assert text not in path.read_text() and "return 17" not in path.read_text()
    assert entry.vector_origin == "caller-provided"
    with pytest.raises(ValueError):
        entry.encoder.repository = "mutated"
    with pytest.raises(ValueError, match="does not match"):
        load_embedding(path, text + " ", "historical-code", config)


@pytest.mark.parametrize("vector", [[1., 2.], [True, 1., 2.], ["1", 1., 2.],
                                   [float("nan"), 1., 2.], [float("inf"), 1., 2.], [10**400, 1., 2.]])
def test_invalid_vectors_fail_before_writing(tmp_path, config, vector):
    path = tmp_path / "bad.json"
    with pytest.raises(ValueError):
        save_embedding(path, "Synthetic", "problem-text", config, vector)
    assert not path.exists() and not list(tmp_path.iterdir())


@pytest.mark.parametrize("change", [{"revision": "main"}, {"tokenizer_revision": ""},
                                   {"max_tokens": True}, {"dimension": 0}, {"pooling": "unknown"},
                                   {"truncation": "unknown"}, {"repository": " "}, {"extra": "field"}])
def test_invalid_encoder_declarations(config, change):
    with pytest.raises(ValueError):
        EncoderConfig.model_validate({**config.model_dump(), **change})


@pytest.mark.parametrize("mutation", [
    lambda p: p["vector"].__setitem__(0, .7), lambda p: p.update(content_sha256="c" * 64),
    lambda p: p["encoder"].update(max_tokens=64), lambda p: p.update(role="historical-code"),
    lambda p: p.update(vector_origin="encoder-produced"), lambda p: p.update(raw_text="forbidden"),
    lambda p: p.update(cache_version="future"),
])
def test_altered_vector_content_config_and_extra_metadata_rejected(tmp_path, config, mutation):
    path = tmp_path / "entry.json"
    save_embedding(path, "Synthetic", "problem-text", config, [0., 1., 2.])
    payload = json.loads(path.read_text())
    mutation(payload)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load_embedding(path, "Synthetic", "problem-text", config)


def test_rehashed_invalid_vector_and_duplicate_json_rejected(tmp_path, config):
    path = tmp_path / "entry.json"
    entry = save_embedding(path, "Synthetic", "problem-text", config, [0., 1., 2.])
    payload = entry.to_dict()
    payload["vector"] = [0., 1.]
    payload["entry_sha256"] = payload_hash({k: v for k, v in payload.items() if k != "entry_sha256"})
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="dimension"):
        load_embedding(path, "Synthetic", "problem-text", config)
    serialized = json.dumps(entry.to_dict())
    path.write_text('{"role":"historical-code",' + serialized[1:])
    with pytest.raises(ValueError, match="Duplicate"):
        load_embedding(path, "Synthetic", "problem-text", config)


def test_atomic_no_replace_failed_link_cleanup_and_revalidated_config(tmp_path, config, monkeypatch):
    path = tmp_path / "entry.json"
    save_embedding(path, "Synthetic", "problem-text", config, [0., 1., 2.])
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        save_embedding(path, "Synthetic", "problem-text", config, [3., 4., 5.])
    assert before == path.read_bytes() and list(tmp_path.iterdir()) == [path]
    def failed_link(*args):
        raise OSError("simulated publication failure")
    monkeypatch.setattr("practice_engine.models.embedding_cache.os.link", failed_link)
    with pytest.raises(OSError, match="publication failure"):
        save_embedding(tmp_path / "failed.json", "Synthetic", "problem-text", config, [0., 1., 2.])
    assert list(tmp_path.iterdir()) == [path]
    with pytest.raises(ValueError):
        make_entry("Synthetic", "problem-text", config.model_copy(update={"dimension": True}), [1., 2., 3.])
    for text, role in [("", "problem-text"), (" ", "problem-text"), ("Synthetic", "candidate-code")]:
        with pytest.raises(ValueError):
            cache_key(text, role, config)


def test_concurrent_writers_publish_one_complete_entry_without_replacing_it(tmp_path, config, monkeypatch):
    import os
    original_link, barrier = os.link, Barrier(2)
    def concurrent_link(source, destination):
        barrier.wait(timeout=10)
        original_link(source, destination)
    monkeypatch.setattr("practice_engine.models.embedding_cache.os.link", concurrent_link)
    path = tmp_path / "concurrent.json"
    def write(value):
        try:
            save_embedding(path, "Synthetic", "problem-text", config, [value, 1., 2.])
            return value
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, [.25, .75]))
    assert outcomes.count(None) == 1
    loaded = load_embedding(path, "Synthetic", "problem-text", config)
    assert loaded.vector[0] == next(value for value in outcomes if value is not None)
    assert list(tmp_path.iterdir()) == [path]
