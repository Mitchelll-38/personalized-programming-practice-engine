"""Paired student uncertainty for aggregate ranking metrics; no data loaders."""

import random

from practice_engine.data.schema import PredictionExample
from .bootstrap import _percentile
from .metrics import _ranking_metrics, evaluate


def paired_student_ranking_bootstrap(examples, candidate_probabilities,
                                     reference_probabilities, *, replicates=1000,
                                     seed=38) -> dict:
    """Conditional percentile intervals using draws containing both classes.

    Resample whole students, retaining multiplicity and pairing across models.
    Higher ranking scores are better, so positive differences favor candidate.
    Undefined one-class draws are counted, never replaced or imputed as zero.
    Callers own partition provenance, locked-test access and runtime budgets.
    """
    if type(replicates) is not int or not 100 <= replicates <= 10000:
        raise ValueError("replicates must be an integer between 100 and 10000")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer between 0 and 2**32-1")
    if not isinstance(examples, (list, tuple)) or not examples or any(
            type(row) is not PredictionExample or type(row.label) is not bool
            or type(row.student_id) is not str or not row.student_id.strip() for row in examples):
        raise ValueError("Nonempty prediction examples with student IDs are required")
    reports = [evaluate(examples, values)["aggregate"] for values in
               (candidate_probabilities, reference_probabilities)]
    students = sorted({row.student_id for row in examples})
    clusters = {student: [] for student in students}
    for index, row in enumerate(examples):
        clusters[row.student_id].append(index)
    groups = [clusters[student] for student in students]
    metrics = ("roc_auc", "incorrect_average_precision")
    samples = {metric: [[], [], []] for metric in metrics}
    rng = random.Random(seed)
    attempted = valid = 0
    if len(students) >= 2:
        for _ in range(replicates):
            indices = [index for _ in students
                       for index in groups[rng.randrange(len(students))]]
            labels = [examples[index].label for index in indices]
            attempted += 1
            if not 0 < sum(labels) < len(labels):
                continue
            valid += 1
            scores = [_ranking_metrics(labels, [values[index] for index in indices])
                      for values in (candidate_probabilities, reference_probabilities)]
            for position, metric in enumerate(metrics):
                candidate, reference = (score[position] for score in scores)
                for bucket, value in zip(samples[metric],
                                         (candidate, reference, candidate - reference)):
                    bucket.append(value)
    reason = ("requires_two_students" if len(students) < 2 else
              "requires_both_classes" if reports[0]["roc_auc"] is None else
              "requires_two_valid_replicates" if valid < 2 else None)
    result = {}
    for metric in metrics:
        estimates = [report[metric] for report in reports]
        estimates.append(None if estimates[0] is None else estimates[0] - estimates[1])
        result[metric] = {
            name: {"estimate": estimate,
                   "interval_95": [_percentile(values, .025), _percentile(values, .975)]
                   if reason is None else None}
            for name, estimate, values in zip(
                ("candidate", "reference", "candidate_minus_reference"),
                estimates, samples[metric])}
    return {"bootstrap_version": "paired-student-ranking-percentile-v1", "seed": seed,
            "requested_replicates": replicates, "attempted_replicates": attempted,
            "valid_replicates": valid, "undefined_replicates": attempted - valid,
            "n_students": len(students), "n_examples": len(examples),
            "interval_method": "linear-interpolated 2.5th/97.5th percentiles",
            "replicate_policy": "conditional_on_both_classes; no replacement draws",
            "undefined_reason": reason, "metrics": result}
