from hashlib import sha256
import json

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, payload_hash
from practice_engine.models.dkt import DKT, ExerciseVocabulary, make_batch
from practice_engine.models.dkt_artifacts import load_dkt_checkpoint, save_dkt_checkpoint


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
