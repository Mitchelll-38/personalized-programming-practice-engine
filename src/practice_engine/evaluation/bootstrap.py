"""Paired cluster uncertainty; no file access, fitting or model selection."""

import math
import random

from practice_engine.data.schema import PredictionExample
from .metrics import evaluate


def _percentile(values, fraction):
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def paired_student_bootstrap(examples, candidate_probabilities, reference_probabilities,
                             *, replicates=1000, seed=38) -> dict:
    """95% percentile intervals on caller-selected examples, paired by student.

    Lower log loss/Brier is better: negative candidate-minus-reference favors
    candidate. Repeated students retain full draw multiplicity in both weightings.
    The caller owns split provenance and any permission to inspect locked tests.
    """
    if type(replicates) is not int or not 100 <= replicates <= 10000:
        raise ValueError("replicates must be an integer between 100 and 10000")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer between 0 and 2**32-1")
    if not isinstance(examples, (list, tuple)) or not examples or any(
            type(row) is not PredictionExample or type(row.label) is not bool
            or type(row.student_id) is not str or not row.student_id.strip() for row in examples):
        raise ValueError("Nonempty prediction examples with student IDs are required")
    reports = [evaluate(examples, values) for values in
               (candidate_probabilities, reference_probabilities)]
    students = sorted(reports[0]["per_student"])
    summaries = [[report["per_student"][student] for student in students] for report in reports]
    n_students = len(students)
    rng = random.Random(seed)
    metrics = ("log_loss", "brier")
    weightings = ("aggregate", "equal_student_macro")
    samples = {(weighting, metric): [[], [], []]
               for weighting in weightings for metric in metrics}
    if n_students >= 2:
        for _ in range(replicates):
            draw = [rng.randrange(n_students) for _ in students]
            count = sum(summaries[0][i]["n_examples"] for i in draw)
            for weighting in weightings:
                for metric in metrics:
                    values = []
                    for summary in summaries:
                        numerator = math.fsum(summary[i][metric] * (
                            summary[i]["n_examples"] if weighting == "aggregate" else 1)
                            for i in draw)
                        values.append(numerator / (count if weighting == "aggregate" else n_students))
                    for bucket, value in zip(samples[weighting, metric],
                                             (*values, values[0] - values[1])):
                        bucket.append(value)
    result = {}
    for weighting in weightings:
        result[weighting] = {}
        for metric in metrics:
            estimates = [report[weighting][metric] for report in reports]
            estimates.append(estimates[0] - estimates[1])
            result[weighting][metric] = {
                name: {"estimate": estimate,
                       "interval_95": [_percentile(values, .025), _percentile(values, .975)]
                       if values else None}
                for name, estimate, values in zip(
                    ("candidate", "reference", "candidate_minus_reference"),
                    estimates, samples[weighting, metric])}
    return {"bootstrap_version": "paired-student-percentile-v1", "seed": seed,
            "requested_replicates": replicates,
            "completed_replicates": replicates if n_students >= 2 else 0,
            "n_students": n_students, "n_examples": len(examples),
            "interval_method": "linear-interpolated 2.5th/97.5th percentiles",
            "undefined_reason": None if n_students >= 2 else "requires_two_students",
            "metrics": result}
