import subprocess
import sys

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance
from practice_engine.models.content_artifacts import load_content_checkpoint, save_content_checkpoint
from practice_engine.models.content_inputs import ConceptVocabulary, make_content_batch
from practice_engine.models.content_lstm import ContentLSTM
from practice_engine.models.content_serving import predict_content_inputs
from practice_engine.models.embedding_cache import EncoderConfig, make_entry
from practice_engine.models.serving import PredictionInput


@pytest.fixture
def prepared(tmp_path):
    encoder = EncoderConfig(repository="synthetic/encoder", revision="a" * 40,
        tokenizer="synthetic/tokenizer", tokenizer_revision="b" * 40, pooling="mean",
        max_tokens=16, truncation="right", dimension=3)
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
        problem_text="Prior", concept_ids=("loops",), correct=False, attempt_number=1,
        submitted_code="return 1;")
    row = PredictionExample(student_id="synthetic", target_sequence_index=1, history=(prior,), label=True,
        candidate=Candidate(problem_id="known", problem_text="Next", concept_ids=("loops",)))
    entries = {}
    for text, role, vector in [("Prior", "problem-text", [1., 2., 3.]),
        ("Next", "problem-text", [3., 2., 1.]), ("Other", "problem-text", [-3., -2., -1.]),
        ("return 1;", "historical-code", [.2, .3, .4])]:
        entry = make_entry(text, role, encoder, vector)
        entries[entry.key_sha256] = entry
    vocabulary = ConceptVocabulary.fit([row])
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(7)
        model = ContentLSTM(vocabulary.size, input_size=3, projection_size=4,
                            concept_size=3, correctness_size=2, hidden_size=5)
    provenance = ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="synthetic-split-v1", split_sha256="b" * 64)
    save_content_checkpoint(tmp_path / "model", model, vocabulary, encoder, provenance)
    return load_content_checkpoint(tmp_path / "model"), row, entries, vocabulary, encoder


def query(row):
    return PredictionInput.model_validate(row.model_dump(exclude={"label"}))


def test_label_free_parity_order_minibatches_cold_unknown_and_content(prepared):
    checkpoint, row, entries, vocabulary, encoder = prepared
    cold = row.model_copy(update={"history": (), "target_sequence_index": 0, "candidate": Candidate(
        problem_id="heldout", problem_text="Next", concept_ids=("unseen",))})
    rows = [row, cold, row]
    expected = torch.sigmoid(checkpoint.logits(make_content_batch(rows, vocabulary, entries, encoder).inputs)).tolist()
    with torch.device("meta"):
        scores = predict_content_inputs(checkpoint, [query(item) for item in rows], entries, batch_size=1)
        assert torch.empty(0).device.type == "meta"
    assert [score.problem_id for score in scores] == ["known", "heldout", "known"]
    assert [score.predicted_correctness for score in scores] == pytest.approx(expected, abs=1e-6)
    changed = cold.model_copy(update={"candidate": cold.candidate.model_copy(update={"problem_text": "Other"})})
    assert predict_content_inputs(checkpoint, [query(changed)], entries)[0].predicted_correctness != scores[1].predicted_correctness
    assert predict_content_inputs(checkpoint, [], entries) == []


def test_revalidation_rejects_label_bearing_and_future_queries(prepared):
    checkpoint, row, entries, *_ = prepared
    with pytest.raises(ValueError, match="PredictionInput"):
        predict_content_inputs(checkpoint, [row], entries)
    forged = query(row).model_copy(update={"target_sequence_index": 0})
    with pytest.raises(ValueError):
        predict_content_inputs(checkpoint, [forged], entries)
    with pytest.raises(ValueError):
        PredictionInput.model_validate({**row.model_dump(), "label": True})


@pytest.mark.parametrize("fault", ["missing", "vector", "config"])
def test_exact_cache_entries_are_required(prepared, fault):
    checkpoint, row, entries, _, encoder = prepared
    key = next(key for key, entry in entries.items() if entry.role == "historical-code")
    if fault == "missing":
        del entries[key]
    elif fault == "vector":
        entries[key] = entries[key].model_copy(update={"vector": (99., 99., 99.)})
    else:
        entries[key] = make_entry("return 1;", "historical-code", encoder.model_copy(update={"pooling": "cls"}), [1., 2., 3.])
    with pytest.raises(ValueError):
        predict_content_inputs(checkpoint, [query(row)], entries)


@pytest.mark.parametrize("mutation", ["weights", "metadata"])
def test_live_integrity_checked_even_for_empty_queries(prepared, mutation):
    checkpoint, _, entries, *_ = prepared
    if mutation == "weights":
        with torch.no_grad():
            checkpoint._model.head.bias.add_(1)
    else:
        checkpoint.metadata.vocabulary["concepts"][0] = "changed"
    with pytest.raises(ValueError):
        predict_content_inputs(checkpoint, [], entries)


@pytest.mark.parametrize("size", [True, 0, 257])
def test_bounded_batch_size(prepared, size):
    checkpoint, row, entries, *_ = prepared
    with pytest.raises(ValueError):
        predict_content_inputs(checkpoint, [query(row)], entries, batch_size=size)


def test_invalid_types_and_checkpoint_outputs_fail(prepared, monkeypatch):
    checkpoint, row, entries, *_ = prepared
    for queries, cache in ((None, entries), (iter([query(row)]), entries), ([query(row)], "a/path")):
        with pytest.raises(ValueError):
            predict_content_inputs(checkpoint, queries, cache)
    with pytest.raises(ValueError):
        predict_content_inputs(object(), [query(row)], entries)
    for logits in (None, torch.ones(2), torch.ones(1, dtype=torch.float64), torch.tensor([float("nan")])):
        monkeypatch.setattr(type(checkpoint), "logits", lambda *args: logits)
        with pytest.raises(ValueError):
            predict_content_inputs(checkpoint, [query(row)], entries)


def test_generic_api_does_not_activate_optional_content_module():
    subprocess.run([sys.executable, "-c", "import sys; import api.main; "
        "assert 'practice_engine.models.content_serving' not in sys.modules; "
        "assert 'torch' not in sys.modules"], check=True)
