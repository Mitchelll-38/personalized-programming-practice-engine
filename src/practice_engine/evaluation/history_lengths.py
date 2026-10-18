"""Fixed history-length evaluation on caller-selected examples; no loaders."""

from practice_engine.data.schema import PredictionExample
from .metrics import evaluate


def evaluate_history_lengths(examples, probabilities) -> dict:
    """Return aggregate metrics for 0, 1-4, 5-19 and 20+ prior responses.

    The caller owns causal histories, source permission and partition access.
    Empty bins contain null scores/prevalence and zero counts. No identifiers,
    predictions or per-student summaries are returned.
    """
    if not isinstance(examples, (list, tuple)) or not examples:
        raise ValueError("Nonempty prediction examples are required")
    for row in examples:
        if (type(row) is not PredictionExample or type(row.label) is not bool
                or type(row.student_id) is not str or not row.student_id.strip()
                or type(row.history) is not tuple):
            raise ValueError("Valid prediction examples with student IDs are required")
        # Frozen models can still be copied with unvalidated updates. Validate
        # nested histories as well before using their lengths for grouping.
        PredictionExample.model_validate(row.model_dump(warnings=False))
    overall = evaluate(examples, probabilities)["aggregate"]
    groups = {name: [] for name in ("0", "1-4", "5-19", "20+")}
    for index, row in enumerate(examples):
        size = len(row.history)
        name = "0" if size == 0 else "1-4" if size < 5 else "5-19" if size < 20 else "20+"
        groups[name].append(index)
    strata = {}
    for name, indices in groups.items():
        if indices:
            strata[name] = evaluate([examples[i] for i in indices],
                                    [probabilities[i] for i in indices])["aggregate"]
        else:
            strata[name] = {
                "n_examples": 0, "n_students": 0, "correct_prevalence": None,
                "log_loss": None, "brier": None, "roc_auc": None,
                "incorrect_average_precision": None,
                "undefined_reasons": {metric: "empty_stratum" for metric in
                    ("correct_prevalence", "log_loss", "brier", "roc_auc",
                     "incorrect_average_precision")},
            }
    return {"history_length_version": "fixed-history-strata-v1",
            "n_examples": overall["n_examples"], "n_students": overall["n_students"],
            "history_length_definition": "number of supplied prior interactions",
            "strata": strata}

