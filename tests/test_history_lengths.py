"""Original synthetic fixtures for fixed history strata and validation."""

import json

import pytest

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.evaluation.history_lengths import evaluate_history_lengths
from practice_engine.evaluation.metrics import evaluate


def example(size, label=True, student="private-student"):
    history = tuple(Interaction(student_id=student, problem_id=f"p{i}",
        sequence_index=i, problem_text="Original synthetic text", concept_ids=("tag",),
        correct=True, attempt_number=1) for i in range(size))
    return PredictionExample(student_id=student, target_sequence_index=size,
        history=history, candidate=Candidate(problem_id="target", problem_text="Original target",
        concept_ids=("tag",)), label=label)


def test_boundaries_conservation_metric_parity_and_privacy():
    rows = [example(size, bool(i % 2)) for i, size in enumerate((0, 1, 4, 5, 19, 20, 21))]
    probabilities = [0, .2, .4, .5, .7, .9, 1]
    report = evaluate_history_lengths(rows, probabilities)
    assert report["n_examples"] == 7
    assert report["n_students"] == 1
    for name, indices in {"0": [0], "1-4": [1, 2], "5-19": [3, 4], "20+": [5, 6]}.items():
        assert report["strata"][name] == evaluate(
            [rows[i] for i in indices], [probabilities[i] for i in indices])["aggregate"]
    assert sum(s["n_examples"] for s in report["strata"].values()) == 7
    encoded = json.dumps(report, allow_nan=False)
    assert "private-student" not in encoded
    assert "Original" not in encoded
    assert "per_student" not in encoded


def test_empty_and_single_class_bins_are_explicit():
    report = evaluate_history_lengths([example(0)], [.8])
    assert report["strata"]["0"]["roc_auc"] is None
    assert report["strata"]["0"]["undefined_reasons"]["roc_auc"] == "requires_both_classes"
    for name in ("1-4", "5-19", "20+"):
        empty = report["strata"][name]
        assert empty["n_examples"] == empty["n_students"] == 0
        assert empty["log_loss"] is empty["brier"] is empty["correct_prevalence"] is None
        assert set(empty["undefined_reasons"].values()) == {"empty_stratum"}


def test_distinct_student_counts_are_local_not_additive():
    rows = [example(0, student="A"), example(1, student="A"), example(1, student="B")]
    report = evaluate_history_lengths(rows, [.5] * 3)
    assert report["n_students"] == 2
    assert report["strata"]["0"]["n_students"] == 1
    assert report["strata"]["1-4"]["n_students"] == 2


@pytest.mark.parametrize("probabilities", [[], [.5, .5], [True], [float("nan")],
    [float("inf")], [-.1], [1.1]])
def test_probability_boundary_validated_before_grouping(probabilities):
    with pytest.raises(ValueError):
        evaluate_history_lengths([example(20)], probabilities)


@pytest.mark.parametrize("rows", [[], [{}], [example(0).model_copy(update={"label": 1})],
    [example(0).model_copy(update={"student_id": None})],
    [example(0).model_copy(update={"student_id": " "})],
    [example(0).model_copy(update={"history": None})],
    [example(0).model_copy(update={"history": ("invalid",)})]])
def test_invalid_examples(rows):
    with pytest.raises(ValueError):
        evaluate_history_lengths(rows, [.5])
