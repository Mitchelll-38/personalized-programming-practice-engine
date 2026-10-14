import json

import pytest

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, save_rate_artifact
from practice_engine.models.bkt import BKTBaseline
from practice_engine.models.logistic import LogisticBaseline
from practice_engine.models.portable import save_baseline_artifact
from practice_engine.models.rates import RateBaseline
from practice_engine.models.serving import PredictionInput, predict_inputs


def query(problem="new"):
    return PredictionInput(student_id="synthetic", target_sequence_index=1, history=(),
        candidate=Candidate(problem_id=problem, problem_text="Original synthetic sum", concept_ids=("loops",)))


@pytest.fixture
def provenance():
    return ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)


def training(label):
    return PredictionExample(student_id="synthetic", target_sequence_index=0, history=(),
        candidate=Candidate(problem_id="known", problem_text="Synthetic sum", concept_ids=("loops",)), label=label)


def test_unknown_rate_fallback_order_and_no_response_fields(tmp_path, provenance):
    artifact = save_rate_artifact(tmp_path / "model.json", RateBaseline.fit([training(True)] * 2), provenance)
    rows = predict_inputs(artifact, [query("z"), query("a")])
    assert [r.model_dump() for r in rows] == [
        {"problem_id": "z", "predicted_correctness": .75},
        {"problem_id": "a", "predicted_correctness": .75}]
    serialized = json.loads(query().model_dump_json())
    assert "label" not in serialized and "correct" not in serialized["candidate"]
    assert predict_inputs(artifact, []) == []
    artifact.model_payload["alpha"] = 2.0
    with pytest.raises(ValueError, match="hash"):
        predict_inputs(artifact, [query()])


@pytest.mark.parametrize("kind", ["logistic", "bkt"])
def test_portable_baselines_accept_label_free_queries(tmp_path, provenance, kind):
    model_class = LogisticBaseline if kind == "logistic" else BKTBaseline
    artifact = save_baseline_artifact(tmp_path / "model.json", model_class.fit([training(True), training(False)]), provenance)
    rows = predict_inputs(artifact, [query()])
    assert len(rows) == 1 and 0 <= rows[0].predicted_correctness <= 1


@pytest.mark.parametrize("field", ["label", "correct", "submitted_code", "target_correct"])
def test_client_target_response_fields_rejected(field):
    body = json.loads(query().model_dump_json())
    body[field] = True
    with pytest.raises(ValueError):
        PredictionInput.model_validate(body)
    body.pop(field)
    body["candidate"][field] = True
    with pytest.raises(ValueError):
        PredictionInput.model_validate(body)


@pytest.mark.parametrize("change", [
    {"problem_id": " "}, {"problem_text": " "}, {"concept_ids": ()},
    {"concept_ids": ("loops", "loops")}, {"concept_ids": (" ",)},
])
def test_bad_candidate_metadata_rejected(change):
    with pytest.raises(ValueError):
        PredictionInput.model_validate({**query().model_dump(), "candidate": {**query().candidate.model_dump(), **change}})


def test_future_wrong_student_retry_candidate_history_and_model_copy_rejected(tmp_path, provenance):
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
        problem_text="Synthetic prior", concept_ids=("loops",), correct=True, attempt_number=1)
    for change in [{"sequence_index": 1}, {"student_id": "other"}, {"attempt_number": 2}, {"problem_id": "new"}]:
        with pytest.raises(ValueError):
            PredictionInput.model_validate({**query().model_dump(), "history": [prior.model_copy(update=change).model_dump()]})
    artifact = save_rate_artifact(tmp_path / "model.json", RateBaseline.fit([training(True)]), provenance)
    bypassed = query().model_copy(update={"target_sequence_index": True})
    with pytest.raises(ValueError):
        predict_inputs(artifact, [bypassed])


def test_unsupported_artifact_and_query_types_rejected():
    with pytest.raises(ValueError, match="artifacts"):
        predict_inputs(object(), [])
    # Rejected before invoking any model or interpreting response fields.
    with pytest.raises(ValueError):
        predict_inputs(object(), [{"label": True}])
