"""Original synthetic cluster fixtures; no acquired student records."""

import json
import math
import random

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.evaluation.bootstrap import paired_student_bootstrap
from practice_engine.evaluation.metrics import evaluate


def example(student, label=True):
    return PredictionExample(student_id=student, target_sequence_index=0, history=(),
        candidate=Candidate(problem_id="synthetic", problem_text="Original fixture", concept_ids=("tag",)),
        label=label)


def test_cluster_multiplicity_and_both_weightings_are_paired(monkeypatch):
    from practice_engine.evaluation import bootstrap
    # Each draw is A,A,B. C is omitted; A contributes twice with all its rows.
    class FixedDraw:
        def __init__(self, seed):
            self.i = 0
        def randrange(self, n):
            self.i += 1
            return (0, 0, 1)[(self.i - 1) % 3]
    rows = [example("A"), example("A"), example("B"), example("C")]
    p, q = [.8, .8, .4, .1], [.6, .6, .2, .3]
    with monkeypatch.context() as context:
        context.setattr(bootstrap.random, "Random", FixedDraw)
        report = paired_student_bootstrap(rows, p, q, replicates=100)
    for weighting, weights in (("aggregate", (4, 1)), ("equal_student_macro", (2, 1))):
        for metric, loss in (("log_loss", lambda x: -math.log(x)), ("brier", lambda x: (1-x)**2)):
            expected = [(weights[0]*loss(v[0]) + weights[1]*loss(v[2])) / sum(weights) for v in (p, q)]
            expected.append(expected[0] - expected[1])
            for name, value in zip(("candidate", "reference", "candidate_minus_reference"), expected):
                assert report["metrics"][weighting][metric][name]["interval_95"] == pytest.approx([value, value])
    assert report["completed_replicates"] == 100


def test_identical_models_have_zero_paired_difference_and_existing_point_metrics():
    rows = [example("A", False), example("A"), example("B"), example("C", False)]
    probabilities = [0, .8, 1, .3]
    result = paired_student_bootstrap(rows, probabilities, probabilities)
    expected = evaluate(rows, probabilities)
    for weighting in ("aggregate", "equal_student_macro"):
        for metric in ("log_loss", "brier"):
            values = result["metrics"][weighting][metric]
            assert values["candidate"]["estimate"] == expected[weighting][metric]
            assert values["candidate_minus_reference"] == {"estimate": 0., "interval_95": [0., 0.]}


def test_repeatability_permutation_privacy_and_rng_isolation():
    rows = [example("private-B"), example("private-A", False), example("private-B", False)]
    p, q = [.7, .8, .1], [.4, .6, .2]
    before = random.getstate()
    first = paired_student_bootstrap(rows, p, q, replicates=100)
    assert random.getstate() == before
    assert first == paired_student_bootstrap(rows, p, q, replicates=100)
    assert first == paired_student_bootstrap(list(reversed(rows)), p[::-1], q[::-1], replicates=100)
    assert "private-" not in json.dumps(first)
    assert p == [.7, .8, .1] and q == [.4, .6, .2]


def test_one_student_has_estimates_but_no_population_interval():
    result = paired_student_bootstrap([example("A")], [.8], [.6])
    assert result["undefined_reason"] == "requires_two_students"
    assert result["completed_replicates"] == 0
    assert result["metrics"]["aggregate"]["log_loss"]["candidate"]["interval_95"] is None


def test_linear_interpolated_percentile_is_explicit():
    from practice_engine.evaluation.bootstrap import _percentile
    assert _percentile([4., 0., 2.], .025) == pytest.approx(.1)
    assert _percentile([4., 0., 2.], .975) == pytest.approx(3.9)


@pytest.mark.parametrize("config", [{"seed": True}, {"seed": -1}, {"seed": 2**32},
    {"replicates": True}, {"replicates": 99}, {"replicates": 10001}, {"replicates": 100.0}])
def test_invalid_resource_and_seed_configuration(config):
    with pytest.raises(ValueError):
        paired_student_bootstrap([example("A")], [.5], [.5], **config)


@pytest.mark.parametrize("p,q", [([], [.5]), ([.5], []), ([True], [.5]),
    ([float("nan")], [.5]), ([.5], [float("inf")]), ([1.1], [.5])])
def test_both_probability_vectors_are_validated(p, q):
    with pytest.raises(ValueError):
        paired_student_bootstrap([example("A")], p, q)


@pytest.mark.parametrize("rows", [[], [{}], [example(" ")]])
def test_invalid_examples_fail_without_echoing_identifiers(rows):
    with pytest.raises(ValueError, match="prediction examples"):
        paired_student_bootstrap(rows, [.5], [.5])
