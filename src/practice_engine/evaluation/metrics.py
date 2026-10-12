"""Probability metrics with explicit ties, class direction and student weighting."""

from collections import defaultdict
from itertools import groupby
import math

from practice_engine.data.schema import PredictionExample


LOG_LOSS_EPSILON = 1e-15


def _ranking_metrics(labels: list[bool], probabilities: list[float]) -> tuple[float, float]:
    correct_count = sum(labels)
    incorrect_count = len(labels) - correct_count
    pairs = sorted(zip(probabilities, labels))
    negatives_below = 0
    wins = 0.0
    for _, group in groupby(pairs, key=lambda pair: pair[0]):
        tied = [label for _, label in group]
        positives = sum(tied)
        negatives = len(tied) - positives
        wins += positives * (negatives_below + 0.5 * negatives)
        negatives_below += negatives
    roc_auc = wins / (correct_count * incorrect_count)

    # Reverse correctness scores: lower p(correct) ranks incorrect targets first.
    cumulative_incorrect = 0
    cumulative_total = 0
    average_precision = 0.0
    for _, group in groupby(pairs, key=lambda pair: pair[0]):
        tied = [label for _, label in group]
        new_incorrect = len(tied) - sum(tied)
        cumulative_total += len(tied)
        cumulative_incorrect += new_incorrect
        average_precision += (new_incorrect / incorrect_count) * (
            cumulative_incorrect / cumulative_total
        )
    return roc_auc, average_precision


def _summary(labels: list[bool], probabilities: list[float], n_students: int) -> dict:
    count = len(labels)
    loss_terms = []
    for label, probability in zip(labels, probabilities):
        clipped = min(1 - LOG_LOSS_EPSILON, max(LOG_LOSS_EPSILON, probability))
        loss_terms.append(-math.log(clipped) if label else -math.log1p(-clipped))
    both_classes = 0 < sum(labels) < count
    roc_auc, average_precision = _ranking_metrics(labels, probabilities) if both_classes else (None, None)
    return {
        "n_examples": count, "n_students": n_students,
        "correct_prevalence": sum(labels) / count,
        "log_loss": math.fsum(loss_terms) / count,
        "brier": math.fsum((p - y) ** 2 for y, p in zip(labels, probabilities)) / count,
        "roc_auc": roc_auc, "incorrect_average_precision": average_precision,
        "undefined_reasons": {} if both_classes else {
            "roc_auc": "requires_both_classes",
            "incorrect_average_precision": "requires_both_classes",
        },
    }


def evaluate(examples: list[PredictionExample], probabilities: list[float]) -> dict:
    """Evaluate caller-selected examples; never fit, calibrate or choose thresholds.

    Input probabilities mean p(correct). Partition ownership and locked-test
    access remain caller responsibilities. Undefined ranking metrics are null.
    """
    if not examples:
        raise ValueError("Evaluation examples must be nonempty")
    if len(examples) != len(probabilities):
        raise ValueError("Examples and probabilities must have equal lengths")
    if any(isinstance(p, bool) or not isinstance(p, (int, float)) or
           not 0 <= p <= 1 or not math.isfinite(p) for p in probabilities):
        raise ValueError("Probabilities must be finite numbers between 0 and 1, excluding bool")
    by_student: dict[str, list[tuple[bool, float]]] = defaultdict(list)
    for example, probability in zip(examples, probabilities):
        by_student[example.student_id].append((example.label, probability))
    per_student = {}
    for student in sorted(by_student):
        labels, scores = zip(*by_student[student])
        per_student[student] = _summary(list(labels), list(scores), 1)
    return {
        "aggregate": _summary([e.label for e in examples], probabilities, len(by_student)),
        "per_student": per_student,
        "equal_student_macro": {
            "n_students": len(by_student),
            **{metric: math.fsum(summary[metric] for summary in per_student.values()) / len(by_student)
               for metric in ("log_loss", "brier")},
        },
        "metric_definitions": {
            "probability": "p(correct)",
            "log_loss": "mean binary negative log likelihood; natural log; fixed clipping",
            "log_loss_epsilon": LOG_LOSS_EPSILON,
            "brier": "mean squared error of raw p(correct)",
            "roc_auc": "correct-positive Mann-Whitney probability; tied scores count one half",
            "incorrect_average_precision": "incorrect-positive step average precision; tied scores grouped; not trapezoidal PR area",
            "one_class_policy": "ranking metrics require both classes",
            "equal_student_macro": "unweighted mean of per-student log_loss and brier",
        },
    }
