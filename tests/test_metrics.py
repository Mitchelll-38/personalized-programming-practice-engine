"""Original synthetic prediction examples with hand-computed metric expectations."""

import math

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.evaluation import evaluate


def example(label, student="s1", index=0):
    return PredictionExample(student_id=student, target_sequence_index=index, history=(),
                             candidate=Candidate(problem_id="synthetic", problem_text="Sum",
                                                 concept_ids=("loops",)), label=label)


def test_hand_computed_probability_and_ranking_metrics():
    examples = [example(y) for y in (True, False, True, False)]
    report = evaluate(examples, [0.8, 0.4, 0.6, 0.7])
    metrics = report["aggregate"]
    assert metrics["n_examples"] == 4 and metrics["n_students"] == 1
    assert metrics["correct_prevalence"] == 0.5
    assert metrics["log_loss"] == pytest.approx(-math.log(0.8 * 0.6 * 0.6 * 0.3) / 4)
    assert metrics["brier"] == pytest.approx((0.04 + 0.16 + 0.16 + 0.49) / 4)
    assert metrics["roc_auc"] == 0.75
    assert metrics["incorrect_average_precision"] == pytest.approx((1 + 2 / 3) / 2)
    assert metrics["undefined_reasons"] == {}


def test_ties_are_grouped_and_independent_of_row_order():
    examples = [example(y) for y in (True, False, True, False)]
    probabilities = [0.9, 0.5, 0.5, 0.1]
    report = evaluate(examples, probabilities)
    assert report["aggregate"]["roc_auc"] == 0.875
    assert report["aggregate"]["incorrect_average_precision"] == pytest.approx((1 + 2 / 3) / 2)
    assert report == evaluate(list(reversed(examples)), list(reversed(probabilities)))
    all_tied = evaluate(examples, [0.5] * 4)["aggregate"]
    assert all_tied["roc_auc"] == 0.5
    assert all_tied["incorrect_average_precision"] == 0.5


def test_class_direction_perfect_and_reversed_rankings():
    examples = [example(True), example(False)]
    perfect = evaluate(examples, [1.0, 0.0])["aggregate"]
    assert perfect["roc_auc"] == perfect["incorrect_average_precision"] == 1
    assert perfect["brier"] == 0
    reversed_scores = evaluate(examples, [0.0, 1.0])["aggregate"]
    assert reversed_scores["roc_auc"] == 0
    assert reversed_scores["incorrect_average_precision"] == 0.5
    assert math.isfinite(reversed_scores["log_loss"])
    assert reversed_scores["brier"] == 1


@pytest.mark.parametrize("label", [True, False])
def test_one_class_metrics_are_explicitly_undefined(label):
    report = evaluate([example(label)], [0.25])
    for metrics in (report["aggregate"], report["per_student"]["s1"]):
        assert metrics["roc_auc"] is None
        assert metrics["incorrect_average_precision"] is None
        assert set(metrics["undefined_reasons"].values()) == {"requires_both_classes"}
        assert math.isfinite(metrics["log_loss"])


def test_equal_student_macro_does_not_overweight_long_histories():
    examples = [example(True, "long") for _ in range(3)] + [example(False, "short")]
    report = evaluate(examples, [0.9] * 4)
    assert report["aggregate"]["brier"] == pytest.approx((3 * 0.01 + 0.81) / 4)
    assert report["equal_student_macro"]["brier"] == pytest.approx((0.01 + 0.81) / 2)
    assert report["equal_student_macro"]["log_loss"] == pytest.approx((-math.log(0.9) - math.log(0.1)) / 2)
    assert list(report["per_student"]) == ["long", "short"]
    assert report["aggregate"]["n_students"] == 2


@pytest.mark.parametrize("probability", [True, False, -0.1, 1.1, 10**400, float("nan"), float("inf"), "0.5", None])
def test_invalid_probabilities_rejected(probability):
    with pytest.raises(ValueError, match="Probabilities"):
        evaluate([example(True)], [probability])


def test_empty_input_and_length_mismatch_rejected():
    with pytest.raises(ValueError, match="nonempty"):
        evaluate([], [])
    with pytest.raises(ValueError, match="equal lengths"):
        evaluate([example(True)], [])
