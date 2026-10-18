from hashlib import sha256
import json

import pytest

torch = pytest.importorskip("torch")

from practice_engine.models.artifacts import ArtifactProvenance, payload_hash
from practice_engine.models.content_artifacts import load_content_checkpoint, save_content_checkpoint
from practice_engine.models.content_inputs import ConceptVocabulary, ContentInputs
from practice_engine.models.content_lstm import ContentLSTM
from practice_engine.models.embedding_cache import EncoderConfig


@pytest.fixture
def prepared(tmp_path):
    vocabulary = ConceptVocabulary(("loops",))
    encoder = EncoderConfig(repository="synthetic/encoder", revision="a" * 40,
        tokenizer="synthetic/tokenizer", tokenizer_revision="b" * 40,
        pooling="mean", max_tokens=16, truncation="right", dimension=3)
    provenance = ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="synthetic-split-v1", split_sha256="b" * 64)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(7)
        model = ContentLSTM(vocabulary.size, input_size=3, projection_size=4,
                            concept_size=3, correctness_size=2, hidden_size=5)
    inputs = ContentInputs(torch.tensor([[[1., 2., 3.]], [[0., 0., 0.]]]),
        torch.ones((2, 1, 3)), torch.tensor([[True], [False]]), torch.tensor([[[2]], [[0]]]),
        torch.tensor([[0], [0]]), torch.tensor([1, 0]), torch.ones((2, 3)), torch.tensor([[2], [1]]))
    return tmp_path / "checkpoint", model, vocabulary, encoder, provenance, inputs


@pytest.fixture
def saved(prepared):
    path, model, vocabulary, encoder, provenance, _ = prepared
    save_content_checkpoint(path, model, vocabulary, encoder, provenance)
    return prepared


def rewrite(path, mutation, *, rehash=True):
    payload = json.loads((path / "metadata.json").read_text())
    mutation(payload)
    if rehash:
        payload["metadata_sha256"] = payload_hash({k: v for k, v in payload.items() if k != "metadata_sha256"})
    (path / "metadata.json").write_text(json.dumps(payload))


def test_parity_detachment_cpu_rng_and_tensor_only_load(saved, monkeypatch):
    path, model, _, encoder, _, inputs = saved
    original = torch.load
    calls = []
    def tracked(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)
    monkeypatch.setattr(torch, "load", tracked)
    rng = torch.random.get_rng_state().clone()
    loaded = load_content_checkpoint(path)
    assert torch.equal(rng, torch.random.get_rng_state())
    assert calls == [{"map_location": "cpu", "weights_only": True}]
    expected = model(inputs).detach()
    assert torch.equal(loaded.logits(inputs), expected)
    assert not loaded.logits(inputs).requires_grad and not loaded._model.training
    assert loaded.metadata.encoder == encoder
    assert all(parameter.device.type == "cpu" and parameter.dtype == torch.float32
               for parameter in loaded._model.parameters())
    with torch.no_grad():
        model.head.bias.add_(10)
    assert torch.equal(loaded.logits(inputs), expected)
    assert {file.name for file in path.iterdir()} == {"metadata.json", "weights.pt"}


def test_restore_pins_cpu_and_preserves_ambient_device_and_rng(saved):
    path, model, _, _, _, inputs = saved
    expected = model(inputs).detach()
    rng = torch.random.get_rng_state().clone()
    prior_device = torch.empty(0).device
    with torch.device("meta"):
        assert torch.empty(0).device.type == "meta"
        loaded = load_content_checkpoint(path)
        assert torch.empty(0).device.type == "meta"
        assert all(parameter.device.type == "cpu" for parameter in loaded._model.parameters())
    assert torch.empty(0).device == prior_device
    assert torch.equal(rng, torch.random.get_rng_state())
    assert torch.equal(loaded.logits(inputs), expected)


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(calibrated=True), lambda p: p.update(feature_version="changed"),
    lambda p: p.update(extra="row data"), lambda p: p["config"].update(hidden_size=True),
    lambda p: p["config"].update(hidden_size=257), lambda p: p["config"].update(input_size=4097),
    lambda p: p["config"].update(concept_vocabulary_size=10001),
    lambda p: p["config"].update(projection_size=0),
    lambda p: p["config"].update(hidden_size=6),
    lambda p: p["vocabulary"].update(concepts=["loops", "loops"]),
    lambda p: p["vocabulary"].update(concepts=["arrays", "loops"]),
    lambda p: p["encoder"].update(dimension=4), lambda p: p["encoder"].update(revision="main"),
    lambda p: p["provenance"].update(fit_partition="validation"),
])
def test_metadata_rejected_even_with_recomputed_hash(saved, mutation):
    path, *_ = saved
    rewrite(path, mutation)
    with pytest.raises(ValueError):
        load_content_checkpoint(path)


@pytest.mark.parametrize("field", ["encoder", "vocabulary", "config", "provenance"])
def test_metadata_hash_binds_every_identity(saved, field):
    path, *_ = saved
    changes = {"encoder": ("pooling", "cls"), "vocabulary": ("concepts", ["arrays"]),
               "config": ("hidden_size", 6), "provenance": ("dataset_version", "different")}
    key, value = changes[field]
    rewrite(path, lambda p: p[field].update({key: value}), rehash=False)
    with pytest.raises(ValueError):
        load_content_checkpoint(path)


@pytest.mark.parametrize("mutation", [
    lambda s: s.pop("head.bias"), lambda s: s.update(extra=torch.ones(1)),
    lambda s: s.update(**{"head.bias": torch.ones(2)}),
    lambda s: s.update(**{"head.bias": s["head.bias"].double()}),
    lambda s: s["head.bias"].fill_(float("nan")),
])
def test_invalid_weights_rejected_even_with_recomputed_hash(saved, mutation):
    path, *_ = saved
    state = torch.load(path / "weights.pt", weights_only=True)
    mutation(state)
    torch.save(state, path / "weights.pt")
    rewrite(path, lambda p: p.update(weights_sha256=sha256((path / "weights.pt").read_bytes()).hexdigest()))
    with pytest.raises(ValueError):
        load_content_checkpoint(path)


def test_corrupted_weights_rejected_before_deserialization(saved, monkeypatch):
    path, *_ = saved
    (path / "weights.pt").write_bytes((path / "weights.pt").read_bytes() + b"corruption")
    monkeypatch.setattr(torch, "load", lambda *a, **k: pytest.fail("unverified bytes deserialized"))
    with pytest.raises(ValueError, match="weights checksum"):
        load_content_checkpoint(path)


def test_architecture_bounds_checked_before_model_allocation(saved, monkeypatch):
    import practice_engine.models.content_artifacts as module
    path, *_ = saved
    rewrite(path, lambda p: p["config"].update(hidden_size=1000000))
    monkeypatch.setattr(module, "ContentLSTM", lambda **k: pytest.fail("unbounded allocation"))
    with pytest.raises(ValueError):
        load_content_checkpoint(path)


@pytest.mark.parametrize("identity", ["encoder", "vocabulary", "provenance"])
def test_save_revalidates_identity_and_alignment(prepared, identity):
    path, model, vocabulary, encoder, provenance, _ = prepared
    if identity == "encoder":
        encoder = encoder.model_copy(update={"dimension": 4})
    elif identity == "vocabulary":
        vocabulary = ConceptVocabulary(("arrays", "loops"))
    else:
        provenance = provenance.model_copy(update={"fit_partition": "validation"})
    with pytest.raises(ValueError):
        save_content_checkpoint(path, model, vocabulary, encoder, provenance)
    assert list(path.parent.iterdir()) == []


def test_duplicate_json_and_live_mutations_rejected(saved):
    path, _, _, _, _, inputs = saved
    loaded = load_content_checkpoint(path)
    loaded.metadata.vocabulary["concepts"][0] = "changed"
    with pytest.raises(ValueError, match="checksum"):
        loaded.logits(inputs)
    loaded = load_content_checkpoint(path)
    with torch.no_grad():
        loaded._model.head.bias.add_(1)
    with pytest.raises(ValueError, match="changed"):
        loaded.logits(inputs)
    loaded = load_content_checkpoint(path)
    loaded._model.lstm.batch_first = False
    with pytest.raises(ValueError, match="semantics"):
        loaded.logits(inputs)
    text = (path / "metadata.json").read_text()
    (path / "metadata.json").write_text(text.replace('"calibrated": false', '"calibrated": false, "calibrated": false'))
    with pytest.raises(ValueError, match="Duplicate"):
        load_content_checkpoint(path)


@pytest.mark.parametrize("change", [lambda m: m.double(), lambda m: m.to("meta"),
    lambda m: m.head.bias.data.fill_(float("inf")), lambda m: setattr(m.concepts, "max_norm", 1.)])
def test_save_rejects_actual_invalid_model_without_publishing(prepared, change):
    path, model, vocabulary, encoder, provenance, _ = prepared
    change(model)
    with pytest.raises(ValueError):
        save_content_checkpoint(path, model, vocabulary, encoder, provenance)
    assert list(path.parent.iterdir()) == []


@pytest.mark.parametrize("point", ["save", "rename"])
def test_publication_failure_cleans_staging_and_lock(prepared, monkeypatch, point):
    import practice_engine.models.content_artifacts as module
    path, model, vocabulary, encoder, provenance, _ = prepared
    def fail(*args):
        raise OSError("injected failure")
    monkeypatch.setattr(torch if point == "save" else module.os, point, fail)
    with pytest.raises(OSError, match="injected"):
        save_content_checkpoint(path, model, vocabulary, encoder, provenance)
    assert list(path.parent.iterdir()) == []


def test_no_clobber_and_cooperating_writer_lock_preserved(saved):
    path, model, vocabulary, encoder, provenance, _ = saved
    before = {file.name: file.read_bytes() for file in path.iterdir()}
    with pytest.raises(FileExistsError):
        save_content_checkpoint(path, model, vocabulary, encoder, provenance)
    assert before == {file.name: file.read_bytes() for file in path.iterdir()}
    other = path.with_name("other")
    lock = other.with_name(".other.publish-lock")
    lock.mkdir()
    with pytest.raises(FileExistsError):
        save_content_checkpoint(other, model, vocabulary, encoder, provenance)
    assert lock.is_dir() and not other.exists()
