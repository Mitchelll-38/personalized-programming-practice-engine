import subprocess
import sys

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance
from practice_engine.models.dkt import DKT, ExerciseVocabulary
from practice_engine.models.dkt_artifacts import load_dkt_checkpoint, save_dkt_checkpoint
from practice_engine.models.dkt_serving import predict_dkt_inputs
from practice_engine.models.serving import PredictionInput


@pytest.fixture
def prepared(tmp_path):
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
        problem_text="Synthetic prior", concept_ids=("loops",), correct=False, attempt_number=1)
    candidate = Candidate(problem_id="known", problem_text="Synthetic next", concept_ids=("loops",))
    row = PredictionExample(student_id="synthetic", target_sequence_index=1,
        history=(prior,), candidate=candidate, label=True)
    vocabulary = ExerciseVocabulary.fit([row])
    with torch.random.fork_rng():
        torch.manual_seed(7)
        model = DKT(vocabulary.size, embedding_size=3, hidden_size=4)
    provenance = ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    save_dkt_checkpoint(tmp_path / "model", model, vocabulary, provenance, training_total=8, training_correct=2)
    query = PredictionInput.model_validate(row.model_dump(exclude={"label"}))
    return load_dkt_checkpoint(tmp_path / "model"), query, row


def test_ordered_known_unknown_cold_start_and_no_target_label(prepared):
    checkpoint, query, row = prepared
    unknown = query.model_copy(update={"candidate": query.candidate.model_copy(update={"problem_id": "new"})})
    cold = query.model_copy(update={"history": (), "target_sequence_index": 0})
    scores = predict_dkt_inputs(checkpoint, [unknown, query, cold])
    assert [score.problem_id for score in scores] == ["new", "known", "known"]
    assert scores[0].predicted_correctness == .3
    assert scores[1].predicted_correctness == checkpoint.predict([row])[0]
    assert all(0 <= score.predicted_correctness <= 1 for score in scores)
    assert predict_dkt_inputs(checkpoint, []) == []
    with pytest.raises(ValueError):
        PredictionInput.model_validate({**query.model_dump(), "label": True})


@pytest.mark.parametrize("change", [{"sequence_index": 1}, {"student_id": "another"},
    {"problem_id": "known"}, {"attempt_number": 2}])
def test_unchecked_future_target_or_retry_queries_rejected(prepared, change):
    checkpoint, query, _ = prepared
    broken = query.model_copy(update={"history": (query.history[0].model_copy(update=change),)})
    with pytest.raises(ValueError):
        predict_dkt_inputs(checkpoint, [broken])
    with pytest.raises(ValueError, match="PredictionInput"):
        predict_dkt_inputs(checkpoint, [query.model_dump()])


def test_live_weights_integrity_preserved(prepared):
    checkpoint, query, _ = prepared
    with torch.no_grad():
        checkpoint._model.head.bias.add_(1)
    with pytest.raises(ValueError, match="weights changed"):
        predict_dkt_inputs(checkpoint, [query])
    with pytest.raises(ValueError, match="reviewed"):
        predict_dkt_inputs(object(), [query])


def test_generic_api_import_remains_lightweight():
    subprocess.run([sys.executable, "-c", "import sys; import api.main; "
        "assert not {'torch','transformers'}.intersection(sys.modules)"], check=True)
