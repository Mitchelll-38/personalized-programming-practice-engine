"""First-attempt task construction and deterministic student-group partitions."""

from collections import defaultdict
from collections.abc import Iterable
from hashlib import sha256
import random

from .schema import Candidate, Interaction, PredictionExample


def validate_problem_metadata(entries: Iterable[tuple[str, str, tuple[str, ...]]]) -> None:
    """Require one statement and concept set for each canonical problem ID."""
    metadata = {}
    for problem_id, problem_text, concept_ids in entries:
        if (not concept_ids or any(type(tag) is not str or not tag.strip() for tag in concept_ids)
                or len(set(concept_ids)) != len(concept_ids)):
            raise ValueError("Problem metadata requires unique nonempty concept IDs")
        identity = (problem_text, frozenset(concept_ids))
        if problem_id in metadata and metadata[problem_id] != identity:
            raise ValueError(f"Problem {problem_id!r} has inconsistent statement or concepts")
        metadata[problem_id] = identity


def first_attempts(rows: list[Interaction]) -> list[Interaction]:
    """Require stable problem metadata and an explicit trustworthy ordering."""
    validate_problem_metadata((row.problem_id, row.problem_text, row.concept_ids) for row in rows)
    by_student: dict[str, list[Interaction]] = defaultdict(list)
    seen_positions: set[tuple[str, int]] = set()
    for row in rows:
        position = (row.student_id, row.sequence_index)
        if position in seen_positions:
            raise ValueError(f"Duplicate or ambiguous sequence index: {position}")
        seen_positions.add(position)
        by_student[row.student_id].append(row)
    result = []
    for student in sorted(by_student):
        seen_problems: dict[str, int] = {}
        for row in sorted(by_student[student], key=lambda x: x.sequence_index):
            previous = seen_problems.get(row.problem_id, 0)
            if row.attempt_number != previous + 1:
                raise ValueError("Attempt numbers must start at 1 and increase per student/problem")
            seen_problems[row.problem_id] = row.attempt_number
            if row.attempt_number == 1:
                result.append(row)
    return result


def prediction_examples(rows: list[Interaction]) -> list[PredictionExample]:
    histories: dict[str, list[Interaction]] = defaultdict(list)
    examples = []
    for target in first_attempts(rows):
        examples.append(PredictionExample(
            student_id=target.student_id,
            target_sequence_index=target.sequence_index,
            history=tuple(histories[target.student_id]),
            candidate=Candidate(
                problem_id=target.problem_id,
                problem_text=target.problem_text,
                concept_ids=target.concept_ids,
            ),
            label=target.correct,
        ))
        histories[target.student_id].append(target)
    return examples


def student_split(rows: list[Interaction], seed: int = 38) -> dict:
    students = sorted({row.student_id for row in rows})
    if len(students) < 3:
        raise ValueError("Need at least three students for nonempty train/validation/test groups")
    random.Random(seed).shuffle(students)
    n_validation = max(1, int(len(students) * 0.15))
    n_test = max(1, int(len(students) * 0.15))
    groups = {
        "train": sorted(students[:-(n_validation + n_test)]),
        "validation": sorted(students[-(n_validation + n_test):-n_test]),
        "test": sorted(students[-n_test:]),
    }
    return {"protocol": "held-out-students", "version": "student-split-v1", "seed": seed,
            "ratios_requested": [0.70, 0.15, 0.15], "student_ids": groups}


def audit(rows: list[Interaction], source_bytes: bytes) -> dict:
    primary = first_attempts(rows)
    return {
        "schema_version": "canonical-v1",
        "source_sha256": sha256(source_bytes).hexdigest(),
        "interactions": len(rows), "first_attempts": len(primary),
        "retries_excluded": len(rows) - len(primary),
        "students": len({r.student_id for r in rows}),
        "problems": len({r.problem_id for r in rows}),
        "concept_ids": sorted({tag for r in rows for tag in r.concept_ids}),
        "first_attempt_success_rate": sum(r.correct for r in primary) / len(primary) if primary else None,
        "label_definition": "Boolean trusted grading outcome of first submission, supplied by importer",
        "prediction_task": "First-attempt correctness on next distinct exercise, including empty-history cold start",
        "ordering": "Explicit per-student sequence_index; ambiguous ties rejected",
        "source_release_verified": False,
        "redistribution_terms_verified": False,
    }
