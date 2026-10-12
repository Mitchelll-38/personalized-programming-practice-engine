import json
from dataclasses import replace

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.dkt import DKT, ExerciseVocabulary, make_batch


def example(count=2, target="target", label=True, student="s1"):
    rows = tuple(Interaction(student_id=student, problem_id=f"p{index}", sequence_index=index,
                             problem_text="Synthetic prior", concept_ids=("loops",),
                             correct=index % 2 == 0, attempt_number=1, submitted_code="unused")
                 for index in range(count))
    return PredictionExample(student_id=student, target_sequence_index=count, history=rows,
                             candidate=Candidate(problem_id=target, problem_text="Synthetic target",
                                                 concept_ids=("loops",)), label=label)


def test_train_only_vocabulary_round_trip_and_unknown_inputs():
    vocabulary = ExerciseVocabulary.fit([example()])
    loaded = ExerciseVocabulary.from_dict(json.loads(json.dumps(vocabulary.to_dict())))
    assert loaded.to_dict() == vocabulary.to_dict()
    assert loaded.size == 5
    assert sorted(loaded.to_dict()["problem_ids"].values()) == [2, 3, 4]
    unseen = example(3, target="validation-only")
    inputs = make_batch([unseen], loaded).inputs
    assert inputs.history_ids[0, 2].item() == 1
    assert inputs.candidate_ids.item() == 1
    assert loaded.to_dict() == vocabulary.to_dict()


@pytest.mark.parametrize("change", [
    {"version": "other"}, {"problem_ids": {"p": 1}}, {"problem_ids": {"p": 3}},
    {"problem_ids": {"p": 2, "q": 2}}, {"problem_ids": {"p": True}},
    {"problem_ids": {" ": 2}}, {"unexpected": "field"},
])
def test_vocabulary_rejects_invalid_json(change):
    payload = {"version": "dkt-exercise-v1", "problem_ids": {"p": 2}} | change
    with pytest.raises(ValueError):
        ExerciseVocabulary.from_dict(payload)


def test_target_labels_code_and_future_other_row_do_not_change_forward():
    before = example()
    changed = before.model_copy(update={"label": False, "history": tuple(
        row.model_copy(update={"submitted_code": "secret", "problem_text": "changed"}) for row in before.history
    )})
    vocabulary = ExerciseVocabulary.fit([before])
    torch.manual_seed(7)
    model = DKT(vocabulary.size).eval()
    original = make_batch([before], vocabulary)
    after = make_batch([changed, example(5, student="unrelated", target="future")], vocabulary)
    assert original.labels.item() == 1 and after.labels[0].item() == 0
    assert not hasattr(after.inputs, "labels")
    torch.testing.assert_close(model(original.inputs)[0], model(after.inputs)[0])


def test_padding_invariance_cold_start_and_candidate_head_bias():
    vocabulary = ExerciseVocabulary.fit([example()])
    model = DKT(vocabulary.size).eval()
    batch = make_batch([example(), example(0)], vocabulary)
    padded = replace(batch.inputs,
                     history_ids=torch.cat((batch.inputs.history_ids, torch.full((2, 4), 999)), 1),
                     history_correct=torch.cat((batch.inputs.history_correct, torch.full((2, 4), 999)), 1))
    torch.testing.assert_close(model(batch.inputs), model(padded))
    candidate = batch.inputs.candidate_ids[1]
    torch.testing.assert_close(model(batch.inputs)[1], model.head.bias[candidate])
    all_empty = make_batch([example(0, target="unseen")], vocabulary)
    torch.testing.assert_close(model(all_empty.inputs)[0], model.head.bias[1])
    loss = torch.nn.functional.binary_cross_entropy_with_logits(model(batch.inputs), batch.labels)
    loss.backward()
    assert model.lstm.weight_ih_l0.grad is not None


@pytest.mark.parametrize("change", [
    {"student_id": "other"}, {"sequence_index": 2}, {"attempt_number": 2}, {"problem_id": "target"},
])
def test_batch_reuses_causal_history_validator(change):
    original = example()
    vocabulary = ExerciseVocabulary.fit([original])
    bad = original.model_copy(update={"history": (original.history[0].model_copy(update=change),)})
    with pytest.raises(ValueError):
        make_batch([bad], vocabulary)


def test_batch_and_forward_reject_invalid_boundaries():
    vocabulary = ExerciseVocabulary.fit([example()])
    with pytest.raises(ValueError, match="nonempty"):
        make_batch([], vocabulary)
    with pytest.raises(ValueError, match="nonempty"):
        ExerciseVocabulary.fit([])
    model = DKT(vocabulary.size)
    inputs = make_batch([example()], vocabulary).inputs
    with pytest.raises(ValueError, match="lengths"):
        model(replace(inputs, lengths=torch.tensor([3])))
    with pytest.raises(ValueError, match="candidate"):
        model(replace(inputs, candidate_ids=torch.tensor([0])))
    with pytest.raises(ValueError, match="binary"):
        model(replace(inputs, history_correct=torch.tensor([[2, 0]])))
