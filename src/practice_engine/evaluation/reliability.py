"""Descriptive calibration diagnostics; no fitting or confidence intervals."""

from collections import Counter
from bisect import bisect_right
import math

from practice_engine.data.schema import PredictionExample
from .metrics import _validate_examples


def reliability_summary(examples: list[PredictionExample], probabilities: list[float],
                        *, n_bins: int = 10, weighting: str = "interaction") -> dict:
    """Summarize p(correct) with fixed-width bins and explicit observation weights.

    The caller owns partition access. This function neither selects a model nor
    certifies calibration; finite-sample ECE depends on binning and weighting.
    """
    if not examples or len(examples) != len(probabilities):
        raise ValueError("Examples must be nonempty and aligned with probabilities")
    if any(isinstance(p, bool) or not isinstance(p, (int, float)) or
           not 0 <= p <= 1 or not math.isfinite(p) for p in probabilities):
        raise ValueError("Probabilities must be finite numbers in [0, 1], excluding bool")
    if type(n_bins) is not int or not 1 <= n_bins <= 100:
        raise ValueError("n_bins must be an integer between 1 and 100")
    if weighting not in ("interaction", "student"):
        raise ValueError("weighting must be interaction or student")
    _validate_examples(examples)

    student_counts = Counter(e.student_id for e in examples)
    internal_edges = [i / n_bins for i in range(1, n_bins)]
    bins: list[list[tuple[PredictionExample, float, float]]] = [[] for _ in range(n_bins)]
    for example, probability in zip(examples, probabilities):
        weight = (1 / len(examples) if weighting == "interaction" else
                  1 / (len(student_counts) * student_counts[example.student_id]))
        bins[bisect_right(internal_edges, probability)].append((example, probability, weight))
    summaries = []
    for index, rows in enumerate(bins):
        mass = math.fsum(w for _, _, w in rows)
        mean = math.fsum(p * w for _, p, w in rows) / mass if rows else None
        frequency = math.fsum(e.label * w for e, _, w in rows) / mass if rows else None
        summaries.append({
            "lower": index / n_bins, "upper": (index + 1) / n_bins,
            "upper_inclusive": index == n_bins - 1,
            "n_examples": len(rows), "n_students": len({e.student_id for e, _, _ in rows}),
            "weight_mass": mass, "mean_probability": mean,
            "correct_frequency": frequency,
            "absolute_gap": abs(mean - frequency) if rows else None,
        })
    return {
        "version": "reliability-v1", "probability": "p(correct)",
        "weighting": weighting, "n_examples": len(examples),
        "n_students": len(student_counts), "n_bins": n_bins, "bins": summaries,
        "expected_calibration_error": math.fsum(
            b["weight_mass"] * b["absolute_gap"] for b in summaries if b["n_examples"]),
        "definitions": {
            "bins": "fixed equal widths; lower inclusive; upper exclusive except final bin",
            "interaction": "each interaction has weight 1 / n_examples",
            "student": "each student has total weight 1 / n_students, shared across their interactions",
            "expected_calibration_error": "sum of bin weight mass times absolute probability-frequency gap",
            "limitations": "descriptive finite-sample diagnostic; bin-dependent; no confidence interval or certification",
        },
    }
