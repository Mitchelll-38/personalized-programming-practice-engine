"""Original synthetic ranking clusters, checked against independent pair counting."""

import json
import random
import statistics

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.evaluation.ranking_bootstrap import paired_student_ranking_bootstrap as bootstrap


def example(student, label):
    return PredictionExample(student_id=student, target_sequence_index=0, history=(),
        candidate=Candidate(problem_id="synthetic", problem_text="Original fixture", concept_ids=("tag",)),
        label=label)


def oracle(labels, scores):
    positives = [p for p, y in zip(scores, labels) if y]
    negatives = [p for p, y in zip(scores, labels) if not y]
    auc = sum((p > n) + .5 * (p == n) for p in positives for n in negatives)
    auc /= len(positives) * len(negatives)
    # Each incorrect row contributes precision at its tied score threshold.
    ap = sum(sum(not y for y, p in zip(labels, scores) if p <= score) /
             sum(p <= score for p in scores) for score in negatives) / len(negatives)
    return auc, ap


def test_seeded_expanded_rows_match_pair_counting_and_threshold_oracle():
    rows = [example("A", False), example("A", True), example("A", False),
            example("B", True), example("C", False)]
    p, q = [0, .5, .5, 1, .3], [.5, .5, .1, .3, 1]
    result = bootstrap(rows, p, q, replicates=200)
    rng = random.Random(38)
    samples = [[[], [], []] for _ in range(2)]
    valid = 0
    for _ in range(200):
        indices = [i for _ in range(3) for i in ((0, 1, 2), (3,), (4,))[rng.randrange(3)]]
        labels = [rows[i].label for i in indices]
        if len(set(labels)) < 2:
            continue
        valid += 1
        scores = [oracle(labels, [vector[i] for i in indices]) for vector in (p, q)]
        for k in range(2):
            for bucket, value in zip(samples[k], (scores[0][k], scores[1][k], scores[0][k]-scores[1][k])):
                bucket.append(value)
    assert result["valid_replicates"] == valid
    assert result["undefined_replicates"] == 200 - valid > 0
    points = [oracle([r.label for r in rows], vector) for vector in (p, q)]
    for k, metric in enumerate(("roc_auc", "incorrect_average_precision")):
        for j, name in enumerate(("candidate", "reference", "candidate_minus_reference")):
            quantiles = statistics.quantiles(samples[k][j], n=40, method="inclusive")
            values = result["metrics"][metric][name]
            assert values["interval_95"] == pytest.approx([quantiles[0], quantiles[-1]])
            assert values["estimate"] == pytest.approx(
                points[j][k] if j < 2 else points[0][k] - points[1][k])


def test_identical_models_privacy_permutation_and_rng_isolation():
    rows = [example("private-B", True), example("private-A", False), example("private-B", False)]
    scores = [.7, .7, 0]
    before = random.getstate()
    result = bootstrap(rows, scores, scores, replicates=100)
    assert random.getstate() == before
    assert result == bootstrap(rows[::-1], scores[::-1], scores[::-1], replicates=100)
    assert "private-" not in json.dumps(result)
    for metric in result["metrics"].values():
        assert metric["candidate_minus_reference"] == {"estimate": 0., "interval_95": [0., 0.]}


@pytest.mark.parametrize("rows,reason,attempted", [
    ([example("A", True), example("A", False)], "requires_two_students", 0),
    ([example("A", True), example("B", True)], "requires_both_classes", 100)])
def test_sparse_inputs_keep_undefined_outputs_explicit(rows, reason, attempted):
    result = bootstrap(rows, [.7, .2], [.3, .8], replicates=100)
    assert result["undefined_reason"] == reason
    assert result["attempted_replicates"] == attempted
    assert result["valid_replicates"] == 0
    for metric in result["metrics"].values():
        assert metric["candidate"]["interval_95"] is None
        assert (metric["candidate"]["estimate"] is None) == (reason == "requires_both_classes")


def test_one_valid_draw_does_not_form_an_interval(monkeypatch):
    from practice_engine.evaluation import ranking_bootstrap
    class SparseDraw:
        def __init__(self, seed):
            self.calls = 0
        def randrange(self, n):
            self.calls += 1
            return int(self.calls == 2)
    monkeypatch.setattr(ranking_bootstrap.random, "Random", SparseDraw)
    result = bootstrap([example("A", True), example("B", False)], [.8, .2], [.2, .8], replicates=100)
    assert result["valid_replicates"] == 1
    assert result["undefined_replicates"] == 99
    assert result["undefined_reason"] == "requires_two_valid_replicates"
    assert result["metrics"]["roc_auc"]["candidate"]["interval_95"] is None


@pytest.mark.parametrize("kwargs", [{"seed": True}, {"seed": -1}, {"seed": 2**32},
    {"replicates": True}, {"replicates": 99}, {"replicates": 10001}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        bootstrap([example("A", True)], [.5], [.5], **kwargs)


@pytest.mark.parametrize("p,q", [([], [.5]), ([.5], []), ([True], [.5]),
    ([float("nan")], [.5]), ([.5], [float("inf")]), ([1.1], [.5])])
def test_validates_both_vectors(p, q):
    with pytest.raises(ValueError):
        bootstrap([example("A", True)], p, q)


@pytest.mark.parametrize("rows", [[], [{}], [example(" ", True)],
    [example("A", True).model_copy(update={"student_id": None})],
    [example("A", True).model_copy(update={"label": 1})]])
def test_invalid_rows(rows):
    with pytest.raises(ValueError, match="prediction examples"):
        bootstrap(rows, [.5], [.5])
