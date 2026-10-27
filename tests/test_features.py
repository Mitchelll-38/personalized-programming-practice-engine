import math

import pytest

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.features import FEATURE_NAMES, FEATURE_VERSION, historical_features


def history(index, correct=True, concepts=("loops",)):
    return Interaction(student_id="s1", problem_id=f"p{index}", sequence_index=index,
                       problem_text="Prior", concept_ids=concepts, correct=correct,
                       attempt_number=1, submitted_code="prior code")


def example(rows=()):
    return PredictionExample(student_id="s1", target_sequence_index=10, history=tuple(rows),
                             candidate=Candidate(problem_id="target", problem_text="Target",
                                                 concept_ids=("loops", "conditions")), label=True)


def test_cold_start_empty_batch_and_fixed_feature_contract():
    assert historical_features([]) == []
    assert historical_features([example()]) == [[0, 0.5, 0, 0.5, 0, 0.5]]
    assert len(FEATURE_NAMES) == 6
    assert FEATURE_VERSION == "historical-numeric-v1"


def test_recent_window_and_shared_concepts_count_interaction_once():
    rows = [history(0), history(1), history(2, False, ("loops", "conditions")),
            history(3, False, ("arrays",)), history(4, False, ("arrays",)),
            history(5, False, ("arrays",)), history(6, False, ("arrays",))]
    assert historical_features([example(rows)])[0] == pytest.approx([
        math.log1p(7), 3 / 9, math.log1p(5), 1 / 7, math.log1p(3), 3 / 5,
    ])


def test_target_label_text_and_code_cannot_change_features():
    before = example([history(0), history(1, False)])
    changed = before.model_copy(update={
        "label": False,
        "candidate": before.candidate.model_copy(update={"problem_text": "SECRET", "problem_id": "other"}),
        "history": tuple(r.model_copy(update={"submitted_code": "CHANGED", "problem_text": "CHANGED"})
                         for r in before.history),
    })
    assert historical_features([before]) == historical_features([changed])


def test_changing_candidate_concepts_only_changes_overlap_features():
    before = example([history(0), history(1, False, ("arrays",))])
    after = before.model_copy(update={"candidate": before.candidate.model_copy(update={"concept_ids": ("unknown",)})})
    old, new = historical_features([before, after])
    assert old[:4] == new[:4]
    assert old[4:] == pytest.approx([math.log1p(1), 2 / 3])
    assert new[4:] == [0, 0.5]


@pytest.mark.parametrize("rows, message", [
    ([history(0).model_copy(update={"student_id": "other"})], "target student"),
    ([history(10)], "before target"),
    ([history(1), history(0)], "strictly ordered"),
    ([history(0), history(0).model_copy(update={"problem_id": "different"})], "strictly ordered"),
    ([history(0).model_copy(update={"attempt_number": 2})], "first attempts"),
    ([history(0), history(1).model_copy(update={"problem_id": "p0"})], "first attempts"),
    ([history(0).model_copy(update={"problem_id": "target"})], "candidate response"),
])
def test_corrupt_direct_history_rejected(rows, message):
    with pytest.raises(ValueError, match=message):
        historical_features([example(rows)])


@pytest.mark.parametrize("correct", [1, 2, "yes", None])
def test_unchecked_nested_outcome_cannot_change_history_rates(correct):
    row = example([history(0, False)])
    copied = row.model_copy(update={"history": (row.history[0].model_copy(update={"correct": correct}),)})
    with pytest.raises(ValueError):
        historical_features([copied])


def test_noncanonical_direct_examples_rejected():
    with pytest.raises(ValueError):
        historical_features([{}])
    with pytest.raises(ValueError):
        historical_features([example().model_copy(update={"student_id": " "})])
