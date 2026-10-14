"""Hand-computed calibration diagnostics on original synthetic observations."""

import json
import math

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.evaluation.reliability import reliability_summary


def example(label, student="synthetic"):
    return PredictionExample(student_id=student, target_sequence_index=0, history=(),
                             candidate=Candidate(problem_id="sum", problem_text="Sum",
                                                 concept_ids=("loops",)), label=label)


def test_boundaries_empty_bins_and_hand_computed_ece():
    report = reliability_summary([example(y) for y in [False, True, False, True]],
                                 [0, .25, .5, 1], n_bins=4)
    bins = report["bins"]
    assert [b["n_examples"] for b in bins] == [1, 1, 1, 1]
    assert [b["mean_probability"] for b in bins] == [0, .25, .5, 1]
    assert [b["upper_inclusive"] for b in bins] == [False, False, False, True]
    assert report["expected_calibration_error"] == .3125
    sparse = reliability_summary([example(True)], [1], n_bins=4)
    assert sparse["bins"][0]["mean_probability"] is None
    assert sparse["bins"][0]["correct_frequency"] is None
    assert sparse["bins"][0]["absolute_gap"] is None
    assert sparse["expected_calibration_error"] == 0
    json.dumps(sparse, allow_nan=False)


def test_equal_student_weighting_does_not_overweight_long_history():
    examples = [example(True, "long")] * 3 + [example(False, "short")]
    interaction = reliability_summary(examples, [.9] * 4, n_bins=1)
    student = reliability_summary(examples, [.9] * 4, n_bins=1, weighting="student")
    assert interaction["expected_calibration_error"] == pytest.approx(.15)
    assert student["expected_calibration_error"] == pytest.approx(.4)
    assert student["bins"][0]["correct_frequency"] == .5
    assert student["bins"][0]["n_students"] == 2
    assert sum(b["weight_mass"] for b in student["bins"]) == 1
    assert student == reliability_summary(list(reversed(examples)), [.9] * 4,
                                         n_bins=1, weighting="student")


@pytest.mark.parametrize("n_bins,index", [(100, 29), (100, 58), (90, 63)])
def test_nonbinary_edges_and_immediately_smaller_scores(n_bins, index):
    edge = index / n_bins
    report = reliability_summary([example(True), example(False)],
                                 [edge, math.nextafter(edge, 0)], n_bins=n_bins)
    assert report["bins"][index]["n_examples"] == 1
    assert report["bins"][index]["mean_probability"] == edge
    assert report["bins"][index - 1]["n_examples"] == 1


def test_bin_mass_and_student_weights_across_bins():
    examples = [example(True, "a"), example(False, "a"), example(False, "b")]
    report = reliability_summary(examples, [.1, .9, .9], n_bins=2, weighting="student")
    assert [b["weight_mass"] for b in report["bins"]] == [.25, .75]
    assert report["expected_calibration_error"] == pytest.approx(.9)


@pytest.mark.parametrize("probability", [True, False, -.1, 1.1, 10**400,
                                            float("nan"), float("inf"), "0.5", None])
def test_bad_scores_rejected(probability):
    with pytest.raises(ValueError, match="Probabilities"):
        reliability_summary([example(True)], [probability])


@pytest.mark.parametrize("kwargs", [{"n_bins": True}, {"n_bins": 0}, {"n_bins": 101},
                                    {"n_bins": 2.0}, {"weighting": "unknown"}])
def test_bad_options_rejected(kwargs):
    with pytest.raises(ValueError):
        reliability_summary([example(True)], [.5], **kwargs)


def test_empty_and_misaligned_inputs_rejected():
    for examples, scores in [([], []), ([example(True)], []), ([], [.5])]:
        with pytest.raises(ValueError, match="aligned"):
            reliability_summary(examples, scores)
