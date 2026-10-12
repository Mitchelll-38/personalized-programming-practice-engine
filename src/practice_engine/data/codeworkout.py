"""Strict adapter for organizer-documented CodeWorkout ProgSnap2 event tables.

This is a format adapter, not a declaration of release access or usage rights.
"""

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from .schema import Candidate, Interaction


@dataclass(frozen=True)
class ImportResult:
    rows: list[Interaction]
    audit: dict


def _table(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
            raise ValueError(f"{path.name}: duplicate column names")
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path.name}: missing columns {sorted(required - set(reader.fieldnames or []))}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"{path.name}: malformed CSV row")
    return rows


def import_codeworkout(release_dir: Path, catalog_path: Path) -> ImportResult:
    """Import scored Run.Program events; fail closed on missing or ambiguous data.

    Catalog is an independently verified JSON array of Candidate objects with
    composite problem_id 'AssignmentID:ProblemID'. Timestamp ties within a
    student are rejected; event IDs and CSV row order never invent chronology.
    """
    catalog = {}
    for entry in json.loads(catalog_path.read_text(encoding="utf-8")):
        candidate = Candidate.model_validate(entry)
        if (not candidate.problem_id.strip() or not candidate.problem_text.strip()
                or not candidate.concept_ids or any(not tag.strip() for tag in candidate.concept_ids)
                or len(set(candidate.concept_ids)) != len(candidate.concept_ids)):
            raise ValueError("Catalog requires problem ID, statement and unique nonempty concepts")
        if candidate.problem_id in catalog:
            raise ValueError("Duplicate catalog problem ID")
        catalog[candidate.problem_id] = candidate
    events = _table(release_dir / "MainTable.csv", {
        "EventID", "SubjectID", "AssignmentID", "ProblemID", "ServerTimestamp",
        "EventType", "Score", "CodeStateID",
    })
    codes = {}
    code_path = release_dir / "CodeStates" / "CodeStates.csv"
    if code_path.exists():
        for state in _table(code_path, {"CodeStateID", "Code"}):
            key = state["CodeStateID"]
            if not key.strip() or key in codes:
                raise ValueError("Empty or duplicate CodeStateID")
            codes[key] = state["Code"]
    by_student = defaultdict(list)
    seen_ids = set()
    event_counts = Counter()
    for event in events:
        event_id = event["EventID"]
        if not event_id.strip() or event_id in seen_ids:
            raise ValueError("Empty or duplicate EventID")
        seen_ids.add(event_id)
        event_counts[event["EventType"]] += 1
        if event["EventType"] != "Run.Program":
            continue
        if any(not event[key].strip() for key in ("SubjectID", "AssignmentID", "ProblemID")):
            raise ValueError(f"Event {event_id}: missing submission key")
        # Colon is the catalog namespace delimiter, never a guessed join.
        if any(":" in event[key] for key in ("AssignmentID", "ProblemID")):
            raise ValueError(f"Event {event_id}: ambiguous composite problem ID")
        problem = f'{event["AssignmentID"]}:{event["ProblemID"]}'
        if problem not in catalog:
            raise ValueError(f"Event {event_id}: missing catalog statement/concepts for {problem}")
        try:
            score = Decimal(event["Score"])
            if not score.is_finite() or not 0 <= score <= 1:
                raise ValueError("out-of-range score")
        except (InvalidOperation, ValueError) as error:
            raise ValueError(f"Event {event_id}: missing/invalid Score") from error
        try:
            if "T" not in event["ServerTimestamp"] and " " not in event["ServerTimestamp"]:
                raise ValueError("Timestamp needs time of day")
            timestamp = datetime.fromisoformat(event["ServerTimestamp"].replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"Event {event_id}: invalid ServerTimestamp") from error
        code_id = event["CodeStateID"]
        if code_id and code_id not in codes:
            raise ValueError(f"Event {event_id}: unresolved CodeStateID")
        by_student[event["SubjectID"]].append((timestamp, problem, score == 1, codes.get(code_id)))
    result = []
    for student, submissions in sorted(by_student.items()):
        if len({time.utcoffset() is None for time, *_ in submissions}) > 1:
            raise ValueError(f"Student {student}: mixed timezone-aware/naive timestamps")
        if len({time for time, *_ in submissions}) != len(submissions):
            raise ValueError(f"Student {student}: ambiguous timestamp tie")
        attempts = Counter()
        for index, (_, problem, correct, code) in enumerate(sorted(submissions, key=lambda row: row[0])):
            attempts[problem] += 1
            candidate = catalog[problem]
            result.append(Interaction(student_id=student, problem_id=problem,
                sequence_index=index, problem_text=candidate.problem_text,
                concept_ids=candidate.concept_ids, correct=correct,
                attempt_number=attempts[problem], submitted_code=code))
    if not result:
        raise ValueError("No scored Run.Program submissions")
    return ImportResult(result, {
        "adapter_version": "codeworkout-progsnap2-v1", "event_rows": len(events),
        "event_type_counts": dict(sorted(event_counts.items())), "scored_submissions": len(result),
        "non_submission_events_excluded": len(events) - len(result),
        "submissions_without_code": sum(row.submitted_code is None for row in result),
        "label_definition": "Score == 1 on first scored Run.Program per student/composite problem; partial scores are incorrect",
        "ordering": "ServerTimestamp per student; ties and mixed timezone-awareness rejected",
        "problem_identity": "AssignmentID:ProblemID (no cross-semester remapping)",
        "source_release_verified": False, "redistribution_terms_verified": False,
    })
