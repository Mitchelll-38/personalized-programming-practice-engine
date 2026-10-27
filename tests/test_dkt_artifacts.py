from hashlib import sha256
import json

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, payload_hash
from practice_engine.models.dkt import DKT, ExerciseVocabulary, make_batch
from practice_engine.models.dkt_artifacts import load_dkt_checkpoint, save_dkt_checkpoint
from torch.nn.modules import module as torch_module


@pytest.fixture
def saved(tmp_path):
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
                        problem_text="Synthetic prior", concept_ids=("loops",), correct=False, attempt_number=1)
    row = PredictionExample(student_id="synthetic", target_sequence_index=1, history=(prior,), label=True,
                            candidate=Candidate(problem_id="p", problem_text="Synthetic", concept_ids=("loops",)))
    vocabulary = ExerciseVocabulary.fit([row])
    torch.manual_seed(7)
    model = DKT(vocabulary.size, embedding_size=4, hidden_size=5)
    with torch.no_grad():
        model.head.bias[1] = 80  # UNK prediction would be 1 if the fallback were omitted.
    provenance = ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
                                    source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    path = tmp_path / "checkpoint"
    kwargs = {"training_total": 8, "training_correct": 2}
    save_dkt_checkpoint(path, model, vocabulary, provenance, **kwargs)
    return path, model, vocabulary, provenance, row, kwargs


def rewrite_metadata(path, mutate):
    payload = json.loads((path / "metadata.json").read_text())
    mutate(payload)
    payload["metadata_sha256"] = payload_hash({key: value for key, value in payload.items() if key != "metadata_sha256"})
    (path / "metadata.json").write_text(json.dumps(payload))


def test_reload_parity_unknown_fallback_label_invariance_and_cpu(saved):
    path, model, vocabulary, _, row, _ = saved
    loaded = load_dkt_checkpoint(path)
    expected = torch.sigmoid(model(make_batch([row], vocabulary).inputs)).item()
    assert loaded.predict([row]) == pytest.approx([expected])
    unknown = row.model_copy(update={"candidate": row.candidate.model_copy(update={"problem_id": "held-out"}), "label": False})
    assert loaded.predict([unknown]) == [0.3]
    assert loaded.predict([row.model_copy(update={"label": False})]) == loaded.predict([row])
    assert loaded.predict([]) == []
    assert all(parameter.device.type == "cpu" for parameter in loaded._model.parameters())
    with torch.no_grad():
        model.head.bias.zero_()
    assert loaded.predict([row]) == pytest.approx([expected])
    loaded.metadata.vocabulary["problem_ids"]["p"] = 3
    with pytest.raises(ValueError):
        loaded.predict([row])


def test_corruption_hashes_and_weights_only_cpu_load(saved, monkeypatch):
    path, *_ = saved
    original = torch.load
    calls = []
    def tracked(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)
    monkeypatch.setattr(torch, "load", tracked)
    load_dkt_checkpoint(path)
    assert calls == [{"map_location": "cpu", "weights_only": True}]
    metadata_path = path / "metadata.json"
    original_metadata = metadata_path.read_bytes()
    payload = json.loads(original_metadata)
    payload["training_correct"] = 3
    metadata_path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Metadata hash"):
        load_dkt_checkpoint(path)
    metadata_path.write_bytes(original_metadata)
    weights = path / "weights.pt"
    weights.write_bytes(weights.read_bytes() + b"corruption")
    with pytest.raises(ValueError, match="Weights hash"):
        load_dkt_checkpoint(path)


def test_duplicate_nested_metadata_field_rejected(saved):
    path, *_ = saved
    metadata = path / "metadata.json"
    serialized = metadata.read_text()
    old = '"source_kind": "synthetic"'
    assert old in serialized
    metadata.write_text(serialized.replace(old, '"source_kind": "unverified", ' + old, 1))
    with pytest.raises(ValueError, match="Duplicate artifact JSON field"):
        load_dkt_checkpoint(path)


@pytest.mark.parametrize("mutation", [
    lambda payload: payload.update(training_total=True), lambda payload: payload.update(training_total=0),
    lambda payload: payload.update(training_correct=9), lambda payload: payload.update(calibrated=True),
    lambda payload: payload["config"].update(hidden_size=0), lambda payload: payload.update(extra="field"),
    lambda payload: payload["vocabulary"]["problem_ids"].update(p=1),
])
def test_malformed_metadata_rejected_even_with_valid_checksum(saved, mutation):
    path, *_ = saved
    rewrite_metadata(path, mutation)
    with pytest.raises(ValueError):
        load_dkt_checkpoint(path)


@pytest.mark.parametrize("mutation", [
    lambda state: state.pop("head.bias"), lambda state: state.update(**{"head.bias": torch.zeros(2)}),
    lambda state: state.update(**{"head.bias": state["head.bias"].to(torch.int64)}),
    lambda state: state["head.bias"].fill_(float("nan")),
])
def test_invalid_state_rejected_even_with_matching_hash(saved, mutation):
    path, *_ = saved
    state = torch.load(path / "weights.pt", weights_only=True)
    mutation(state)
    torch.save(state, path / "weights.pt")
    rewrite_metadata(path, lambda payload: payload.update(weights_sha256=sha256((path / "weights.pt").read_bytes()).hexdigest()))
    with pytest.raises(ValueError, match="state keys|tensor"):
        load_dkt_checkpoint(path)


@pytest.mark.parametrize("counts", [(True, 0), (0, 0), (8, 9), (8, True), (8.0, 2), (8, -1)])
def test_invalid_supplied_training_counts_never_publish(saved, counts):
    path, model, vocabulary, provenance, *_ = saved
    target = path.with_name("invalid-counts")
    with pytest.raises(ValueError):
        save_dkt_checkpoint(target, model, vocabulary, provenance,
                            training_total=counts[0], training_correct=counts[1])
    assert not target.exists() and not list(path.parent.glob(".invalid-counts*"))


def test_existing_destination_untouched_and_failed_publish_cleans_staging(saved, monkeypatch):
    path, model, vocabulary, provenance, _, kwargs = saved
    before = {file.name: file.read_bytes() for file in path.iterdir()}
    with pytest.raises(FileExistsError):
        save_dkt_checkpoint(path, model, vocabulary, provenance, **kwargs)
    assert before == {file.name: file.read_bytes() for file in path.iterdir()}
    def interrupted(*args):
        raise OSError("simulated interrupted publication")
    monkeypatch.setattr("practice_engine.models.dkt_artifacts.os.rename", interrupted)
    target = path.with_name("interrupted")
    with pytest.raises(OSError, match="interrupted"):
        save_dkt_checkpoint(target, model, vocabulary, provenance, **kwargs)
    assert not target.exists() and not list(path.parent.glob(".interrupted*"))


def test_live_weights_mutation_rejected_and_existing_publisher_lock_preserved(saved):
    path, model, vocabulary, provenance, row, kwargs = saved
    loaded = load_dkt_checkpoint(path)
    with torch.no_grad():
        loaded._model.head.bias.add_(1)
    with pytest.raises(ValueError, match="weights changed"):
        loaded.predict([row])
    target = path.with_name("locked")
    lock = target.with_name(".locked.publish-lock")
    lock.mkdir()
    with pytest.raises(FileExistsError):
        save_dkt_checkpoint(target, model, vocabulary, provenance, **kwargs)
    assert lock.is_dir() and not target.exists()


@pytest.mark.parametrize("mutate", [
    lambda model: setattr(model.embedding, "max_norm", 1e-6),
    lambda model: setattr(model.embedding, "norm_type", 1.0),
    lambda model: setattr(model.lstm, "batch_first", False),
    lambda model: setattr(model.head, "in_features", 99),
])
def test_live_architecture_change_rejected_on_first_prediction(saved, mutate):
    path, _, _, _, row, _ = saved
    loaded = load_dkt_checkpoint(path)
    assert len(loaded.predict([row])) == 1
    mutate(loaded._model)
    with pytest.raises(ValueError, match="architecture|semantics"):
        loaded.predict([row])


@pytest.mark.parametrize("mutate", [
    lambda model: setattr(model.embedding, "max_norm", 1e-6),
    lambda model: setattr(model.lstm, "batch_first", False),
    lambda model: setattr(model.head, "in_features", 99),
])
def test_save_rejects_noncanonical_architecture_before_publication(saved, mutate):
    path, model, vocabulary, provenance, _, kwargs = saved
    destination = path.with_name("changed-semantics")
    mutate(model)
    with pytest.raises(ValueError, match="architecture semantics"):
        save_dkt_checkpoint(destination, model, vocabulary, provenance, **kwargs)
    assert not destination.exists()
    assert not destination.with_name(".changed-semantics.publish-lock").exists()


@pytest.mark.parametrize("part", ["model", "embedding", "lstm", "head"])
@pytest.mark.parametrize("kind", ["forward", "pre"])
def test_registered_local_forward_hooks_rejected_on_save_and_predict(saved, part, kind):
    path, model, vocabulary, provenance, row, kwargs = saved
    loaded = load_dkt_checkpoint(path)
    baseline = loaded.predict([row])
    destination = path.with_name("hooked")

    def attach(target):
        module = target if part == "model" else getattr(target, part)
        if kind == "forward":
            return module.register_forward_hook(lambda _module, _inputs, output: output)
        return module.register_forward_pre_hook(lambda _module, inputs: inputs)

    with attach(loaded._model):
        with pytest.raises(ValueError, match="forward hooks"):
            loaded.predict([row])
    assert loaded.predict([row]) == baseline
    with attach(model):
        with pytest.raises(ValueError, match="forward hooks"):
            save_dkt_checkpoint(destination, model, vocabulary, provenance, **kwargs)
    assert not destination.exists()


@pytest.mark.parametrize("kind", ["forward", "pre"])
def test_registered_global_forward_hooks_rejected_on_save_and_predict(saved, kind):
    path, model, vocabulary, provenance, row, kwargs = saved
    loaded = load_dkt_checkpoint(path)
    baseline = loaded.predict([row])
    destination = path.with_name("globally-hooked")
    hook = (torch_module.register_module_forward_hook(
        lambda _module, _inputs, output: output) if kind == "forward" else
        torch_module.register_module_forward_pre_hook(
            lambda _module, inputs: inputs))
    try:
        with pytest.raises(ValueError, match="forward hooks"):
            loaded.predict([row])
        with pytest.raises(ValueError, match="forward hooks"):
            save_dkt_checkpoint(destination, model, vocabulary, provenance, **kwargs)
    finally:
        hook.remove()
    assert loaded.predict([row]) == baseline
    assert not destination.exists()


def test_public_save_and_load_preserve_rng_under_alternate_default_device(saved, tmp_path):
    path, model, vocabulary, provenance, row, kwargs = saved
    expected = load_dkt_checkpoint(path).predict([row])
    before = torch.random.get_rng_state().clone()
    # Meta is a CPU-only test of default-device independence; no GPU is needed.
    with torch.device("meta"):
        destination = tmp_path / "context-checkpoint"
        save_dkt_checkpoint(destination, model, vocabulary, provenance, **kwargs)
        loaded = load_dkt_checkpoint(destination)
        assert torch.empty(0).device.type == "meta"
        assert all(parameter.device.type == "cpu" for parameter in loaded._model.parameters())
    assert torch.empty(0).device.type == "cpu"
    assert torch.equal(before, torch.random.get_rng_state())
    assert loaded.predict([row]) == expected


def test_failed_save_state_validation_preserves_rng_and_default_device(saved, tmp_path):
    _, model, vocabulary, provenance, _, kwargs = saved
    with torch.no_grad():
        model.head.weight[0, 0] = float("nan")
    before = torch.random.get_rng_state().clone()
    destination = tmp_path / "invalid-save"
    with torch.device("meta"):
        with pytest.raises(ValueError, match="Invalid checkpoint tensor"):
            save_dkt_checkpoint(destination, model, vocabulary, provenance, **kwargs)
        assert torch.empty(0).device.type == "meta"
    assert torch.equal(before, torch.random.get_rng_state())
    assert not destination.exists()
    assert not destination.with_name(".invalid-save.publish-lock").exists()


def test_failed_load_state_validation_preserves_rng_and_default_device(saved):
    path, *_ = saved
    weights_path = path / "weights.pt"
    state = torch.load(weights_path, map_location="cpu", weights_only=True)
    del state["head.weight"]
    torch.save(state, weights_path)
    rewrite_metadata(path, lambda payload: payload.update(
        weights_sha256=sha256(weights_path.read_bytes()).hexdigest()))
    before = torch.random.get_rng_state().clone()
    with torch.device("meta"):
        with pytest.raises(ValueError, match="state keys"):
            load_dkt_checkpoint(path)
        assert torch.empty(0).device.type == "meta"
    assert torch.equal(before, torch.random.get_rng_state())
