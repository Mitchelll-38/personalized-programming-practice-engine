import json

import pytest

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models import RateBaseline


def example(problem="p1", label=True, history=()):
    return PredictionExample(
        student_id="s1", target_sequence_index=len(history), history=history,
        candidate=Candidate(problem_id=problem, problem_text="Sum", concept_ids=("loops",)),
        label=label,
    )


def test_smoothing_global_problem_and_unknown_rates():
    model = RateBaseline.fit([example(), example(), example("p2", False)])
    candidates = [example(), example("p2"), example("unknown")]
    assert model.predict(candidates) == pytest.approx([3 / 4, 1 / 3, 3 / 5])
    assert model.predict(candidates, per_problem=False) == pytest.approx([3 / 5] * 3)
    assert model.predict([]) == []


def test_training_and_prediction_ignore_code_history_and_prediction_labels():
    history = (Interaction(student_id="s1", problem_id="earlier", sequence_index=0,
                           problem_text="Earlier", concept_ids=("loops",), correct=False,
                           submitted_code="SECRET", attempt_number=1),)
    train = [example(), example("p2", False)]
    changed = [e.model_copy(update={"history": history, "student_id": "other"}) for e in train]
    assert RateBaseline.fit(train).to_dict() == RateBaseline.fit(changed).to_dict()
    model = RateBaseline.fit(train)
    assert model.predict(train) == model.predict([
        e.model_copy(update={"label": not e.label, "history": history}) for e in train
    ])


def test_json_round_trip_order_and_detached_payload():
    train = [example("z"), example("a", False)]
    model = RateBaseline.fit(train, alpha=2)
    payload = model.to_dict()
    assert list(payload["problem_counts"]) == ["a", "z"]
    assert json.dumps(payload) == json.dumps(RateBaseline.fit(list(reversed(train)), 2).to_dict())
    loaded = RateBaseline.from_dict(json.loads(json.dumps(payload)))
    assert loaded.predict(train) == model.predict(train)
    payload["problem_counts"]["a"]["correct"] = 1
    assert model.to_dict()["problem_counts"]["a"]["correct"] == 0


@pytest.mark.parametrize("alpha", [0, -1, float("nan"), float("inf"), True, "1"])
def test_invalid_smoothing_rejected(alpha):
    with pytest.raises(ValueError):
        RateBaseline.fit([example()], alpha)


def test_empty_training_and_large_finite_smoothing():
    with pytest.raises(ValueError, match="nonempty"):
        RateBaseline.fit([])
    assert RateBaseline.fit([example()], 1e308).predict([example()]) == [0.5]


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(extra="untrusted"),
    lambda p: p.update(alpha=True),
    lambda p: p.update(alpha=float("nan")),
    lambda p: p["global_counts"].update(total=True),
    lambda p: p["global_counts"].update(correct=2),
    lambda p: p["global_counts"].update(total=2),
    lambda p: p["problem_counts"]["p1"].update(correct=-1),
    lambda p: p["problem_counts"].update(other={"total": 1, "correct": 0}),
    lambda p: p.update(problem_counts={"": {"total": 1, "correct": 1}}),
    lambda p: p.update(problem_counts={}),
])
def test_invalid_saved_counts_rejected(mutate):
    payload = RateBaseline.fit([example()]).to_dict()
    mutate(payload)
    with pytest.raises(ValueError):
        RateBaseline.from_dict(payload)
