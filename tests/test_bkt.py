"""Original synthetic examples; analytic updates do not assert empirical accuracy."""

import json

import pytest

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.bkt import BKTBaseline


PARAMS = {"initial": 0.2, "learn": 0.1, "guess": 0.2, "slip": 0.1}


def example(label=True, history=(), concepts=("loops",)):
    return PredictionExample(student_id="s1", target_sequence_index=10, history=tuple(history),
                             candidate=Candidate(problem_id="target", problem_text="Synthetic",
                                                 concept_ids=concepts), label=label)


def observation(correct, index=0):
    return Interaction(student_id="s1", problem_id=f"p{index}", sequence_index=index,
                       problem_text="Synthetic earlier", concept_ids=("loops",), correct=correct,
                       attempt_number=1, submitted_code="synthetic code")


def model():
    return BKTBaseline.from_dict({"version": "shared-bkt-v1", "parameters": PARAMS})


def test_analytic_correct_and_incorrect_bayes_then_learning_updates():
    prior = 0.2
    posterior_correct = prior * 0.9 / (prior * 0.9 + 0.8 * 0.2)
    posterior_incorrect = prior * 0.1 / (prior * 0.1 + 0.8 * 0.8)
    expected = [0.2 + 0.7 * (p + (1 - p) * 0.1) for p in (posterior_correct, posterior_incorrect)]
    assert model().predict([example(history=[observation(True)]),
                            example(history=[observation(False)])]) == pytest.approx(expected)


def test_cold_start_unknown_and_multiconcept_mean():
    baseline = model()
    cold, known, mixed = baseline.predict([
        example(concepts=("unknown",)), example(history=[observation(True)]),
        example(history=[observation(True)], concepts=("loops", "unknown")),
    ])
    assert cold == pytest.approx(0.34)
    assert mixed == pytest.approx((cold + known) / 2)
    assert baseline.predict([]) == []
    assert baseline.predict([example(history=[observation(True)], concepts=("loops", "loops"))]) == [known]
    shared = observation(True).model_copy(update={"concept_ids": ("loops", "unknown")})
    assert baseline.predict([example(history=[shared], concepts=("loops", "unknown"))]) == [known]


def test_prediction_label_text_code_invariance_and_json_reload():
    original = example(history=[observation(True), observation(False, 1)])
    changed = original.model_copy(update={"label": False,
        "candidate": original.candidate.model_copy(update={"problem_text": "changed"}),
        "history": tuple(h.model_copy(update={"submitted_code": "changed"}) for h in original.history)})
    baseline = model()
    assert baseline.predict([original]) == baseline.predict([changed])
    payload = baseline.to_dict()
    assert BKTBaseline.from_dict(json.loads(json.dumps(payload))).predict([original]) == baseline.predict([original])
    payload["parameters"]["initial"] = 0.9
    assert baseline.to_dict()["parameters"]["initial"] == 0.2


def test_grid_train_label_selection_and_deterministic_ties():
    low, high = {**PARAMS, "initial": 0.1}, {**PARAMS, "initial": 0.9}
    positive = [example(), example()]
    assert BKTBaseline.fit(positive, [low, high]).to_dict()["parameters"] == high
    assert BKTBaseline.fit([example(False)], [high, low]).to_dict()["parameters"] == low
    balanced = [example(), example(False)]
    assert BKTBaseline.fit(balanced).to_dict() == BKTBaseline.fit(list(reversed(balanced))).to_dict()
    assert BKTBaseline.fit(positive, [high, low]).to_dict() == BKTBaseline.fit(positive, [low, high]).to_dict()
    tie = {**PARAMS, "learn": 0.0}  # No history: learn cannot affect likelihood.
    assert BKTBaseline.fit(positive, [PARAMS, tie]).to_dict()["parameters"] == tie
    assert BKTBaseline.fit(positive, [tie, PARAMS]).to_dict()["parameters"] == tie


@pytest.mark.parametrize("history", [
    [observation(True, 10)],
    [observation(True).model_copy(update={"problem_id": "target"})],
    [observation(True).model_copy(update={"student_id": "other"})],
    [observation(True).model_copy(update={"attempt_number": 2})],
    [observation(True, 1), observation(True)],
])
def test_invalid_causal_histories_rejected_at_fit_and_predict(history):
    with pytest.raises(ValueError):
        model().predict([example(history=history)])
    with pytest.raises(ValueError):
        BKTBaseline.fit([example(history=history)], [PARAMS])


@pytest.mark.parametrize("parameters", [
    {**PARAMS, "initial": True}, {**PARAMS, "learn": -1}, {**PARAMS, "slip": 0},
    {**PARAMS, "guess": float("nan")}, {**PARAMS, "learn": float("inf")},
    {**PARAMS, "guess": 0.9}, {**PARAMS, "extra": 1},
])
def test_invalid_parameters_rejected_at_fit_and_load(parameters):
    with pytest.raises(ValueError):
        BKTBaseline.fit([example()], [parameters])
    with pytest.raises(ValueError):
        BKTBaseline.from_dict({"version": "shared-bkt-v1", "parameters": parameters})


def test_empty_training_grid_concepts_and_unknown_payload_rejected():
    for examples, grid in (([], [PARAMS]), ([example()], []), ([example()], PARAMS)):
        with pytest.raises(ValueError):
            BKTBaseline.fit(examples, grid)
    with pytest.raises(ValueError):
        model().predict([example(concepts=())])
    with pytest.raises(ValueError):
        model().predict([example(concepts=(" ",))])
    with pytest.raises(ValueError):
        BKTBaseline.from_dict({"version": "unknown", "parameters": PARAMS})
    with pytest.raises(ValueError):
        BKTBaseline.from_dict({**model().to_dict(), "extra": "untrusted"})


@pytest.mark.parametrize("row", [None, {}, example().model_copy(update={"label": 1}),
    example().model_copy(update={"label": 2}),
    example().model_copy(update={"label": "yes"}),
    example().model_copy(update={"label": None}),
    example().model_copy(update={"student_id": " "}),
    example().model_copy(update={"history": ("invalid",)})])
def test_invalid_copied_training_row_cannot_fit_bkt(row):
    with pytest.raises(ValueError):
        BKTBaseline.fit([row, example(False)], [PARAMS])
