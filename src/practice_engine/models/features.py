"""Fixed numeric features computed exclusively from observed causal histories."""

import math

from practice_engine.data.schema import Candidate, Interaction, PredictionExample

FEATURE_VERSION = "historical-numeric-v1"
FEATURE_NAMES = (
    "log1p_history_count", "history_success_rate",
    "log1p_recent_count", "recent_success_rate",
    "log1p_concept_overlap_count", "concept_overlap_success_rate",
)


def validate_training_examples(examples: list[PredictionExample]) -> None:
    """Reject unchecked copies before fitting any labels or features."""
    for row in examples:
        if (type(row) is not PredictionExample or type(row.label) is not bool
                or type(row.student_id) is not str or not row.student_id.strip()):
            raise ValueError("Valid training prediction examples are required")
        PredictionExample.model_validate(row.model_dump(warnings=False))


def _validate_history(example: PredictionExample) -> None:
    if (type(example) is not PredictionExample or type(example.student_id) is not str
            or not example.student_id.strip() or type(example.target_sequence_index) is not int
            or type(example.history) is not tuple or type(example.candidate) is not Candidate
            or type(example.candidate.problem_id) is not str
            or type(example.candidate.concept_ids) is not tuple
            or any(type(tag) is not str for tag in example.candidate.concept_ids)):
        raise ValueError("Valid prediction metadata and history are required")
    previous_index = -1
    problems = set()
    for row in example.history:
        if (type(row) is not Interaction or type(row.student_id) is not str
                or not row.student_id.strip() or type(row.problem_id) is not str
                or not row.problem_id or type(row.sequence_index) is not int
                or type(row.attempt_number) is not int or type(row.correct) is not bool
                or type(row.concept_ids) is not tuple or not row.concept_ids
                or any(type(tag) is not str or not tag.strip() for tag in row.concept_ids)
                or len(set(row.concept_ids)) != len(row.concept_ids)):
            raise ValueError("Valid historical interactions are required")
        if row.student_id != example.student_id:
            raise ValueError("history must belong to the target student")
        if row.sequence_index <= previous_index or row.sequence_index >= example.target_sequence_index:
            raise ValueError("history must be strictly ordered before target")
        if row.attempt_number != 1 or row.problem_id in problems:
            raise ValueError("history must contain distinct first attempts")
        if row.problem_id == example.candidate.problem_id:
            raise ValueError("candidate response cannot appear in history")
        previous_index = row.sequence_index
        problems.add(row.problem_id)


def _summary(rows: tuple[Interaction, ...] | list[Interaction]) -> list[float]:
    # A fixed Beta(1,1) prior is not fitted from any partition's labels.
    return [math.log1p(len(rows)), (sum(row.correct for row in rows) + 1) / (len(rows) + 2)]


def historical_features(examples: list[PredictionExample]) -> list[list[float]]:
    """Return six fixed-order, unscaled numeric features per prediction example.

    Recent means the five most recent observed first attempts. Concept evidence
    counts each prior interaction once if it shares any candidate concept. Empty
    histories have zero counts and rate 0.5. No candidate label, code, text, ID
    vocabulary, student ID feature or learned transform enters the output.
    Invalid direct inputs fail rather than silently accepting future responses.
    """
    features = []
    for example in examples:
        _validate_history(example)
        concepts = set(example.candidate.concept_ids)
        overlap = [row for row in example.history if concepts.intersection(row.concept_ids)]
        features.append(_summary(example.history) + _summary(example.history[-5:]) + _summary(overlap))
    return features
