"""Strict organizer-format mapping; identities are integrity, not use permissions."""

import csv
from dataclasses import dataclass
from hashlib import sha256
import io
import json
from pathlib import Path
import re

from practice_engine.models.artifacts import payload_hash
from .schema import Candidate

CONCEPTS = ("If/Else", "NestedIf", "While", "For", "NestedFor", "Math+-*/", "Math%",
    "LogicAndNotOr", "LogicCompareNum", "LogicBoolean", "StringFormat", "StringConcat",
    "StringIndex", "StringLen", "StringEqual", "CharEqual", "ArrayIndex", "DefFunction")
HEADERS = ("AssignmentID", "ProblemID", "Requirement", *CONCEPTS)
POLICY = {"version": "organizer-catalog-mapping-v1", "headers": list(HEADERS),
    "assignment": "ASCII canonical integer optionally followed by decimal point and zeros; one spelling per side",
    "problem": "exact ASCII canonical integer; no normalization", "identity": "preserve release composite ID",
    "prompt": "preserve parsed Requirement cell verbatim", "concepts": "original header for exact cell 1; blank absent"}


def _assignment(value):
    match = re.fullmatch(r"(0|[1-9][0-9]*)(?:\.0+)?", value)
    if match is None:
        raise ValueError("Unsupported assignment ID spelling")
    return match.group(1)


def _problem(value):
    if re.fullmatch(r"0|[1-9][0-9]*", value) is None:
        raise ValueError("Problem ID must be an exact canonical ASCII integer")
    return value


def _assignment_map(values):
    result = {}
    for value in set(values):
        key = _assignment(value)
        if key in result and result[key] != value:
            raise ValueError("Ambiguous assignment normalization collision")
        result[key] = value
    return result


@dataclass(frozen=True)
class CatalogMapping:
    candidates: tuple[Candidate, ...]
    _receipt_json: str

    @property
    def receipt(self) -> dict:
        """Detach nested maps/lists so callers cannot alter the saved snapshot."""
        return json.loads(self._receipt_json)


def map_organizer_catalog(csv_path: Path, release_problem_ids: list[str] | tuple[str, ...]) -> CatalogMapping:
    if (not isinstance(release_problem_ids, (list, tuple)) or not release_problem_ids
            or any(not isinstance(value, str) for value in release_problem_ids)
            or len(set(release_problem_ids)) != len(release_problem_ids)):
        raise ValueError("Explicit unique nonempty release composite-ID inventory required")
    inventory = tuple(release_problem_ids)
    release_pairs = []
    for value in inventory:
        if value.count(":") != 1:
            raise ValueError("Release IDs require AssignmentID:ProblemID")
        assignment, problem = value.split(":")
        _assignment(assignment)
        release_pairs.append((assignment, _problem(problem)))
    release_assignments = _assignment_map(a for a, _ in release_pairs)
    serialized = Path(csv_path).read_bytes()
    try:
        reader = csv.reader(io.StringIO(serialized.decode("utf-8-sig"), newline=""), strict=True)
        header, rows = tuple(next(reader, ())), list(reader)
    except csv.Error as error:
        raise ValueError("Malformed catalog CSV") from error
    if header != HEADERS:
        raise ValueError("Catalog requires exact known organizer headers in order")
    if not rows or any(len(row) != len(HEADERS) for row in rows):
        raise ValueError("Catalog rows must match the complete known format")
    catalog_pairs = [(row[0], _problem(row[1])) for row in rows]
    if len(set(catalog_pairs)) != len(catalog_pairs):
        raise ValueError("Duplicate catalog composite ID")
    catalog_assignments = _assignment_map(a for a, _ in catalog_pairs)
    if set(catalog_assignments) != set(release_assignments):
        raise ValueError("Catalog/release assignment coverage differs")
    crosswalk = {catalog_assignments[key]: release_assignments[key] for key in sorted(catalog_assignments)}
    candidates = []
    for row in rows:
        if not row[2].strip() or any(value not in ("", "1") for value in row[3:]):
            raise ValueError("Catalog needs nonempty prompts and exact blank/1 concept cells")
        concepts = tuple(name for name, value in zip(CONCEPTS, row[3:]) if value == "1")
        if not concepts:
            raise ValueError("Each catalog problem needs a positive concept annotation")
        candidates.append(Candidate(problem_id=f"{crosswalk[row[0]]}:{row[1]}",
                                    problem_text=row[2], concept_ids=concepts))
    if {candidate.problem_id for candidate in candidates} != set(inventory):
        raise ValueError("Catalog/release problem coverage differs")
    candidates = tuple(sorted(candidates, key=lambda candidate: candidate.problem_id))
    crosswalk_payload = {"assignment_crosswalk": crosswalk}
    receipt = {"mapping_version": POLICY["version"], "catalog_sha256": sha256(serialized).hexdigest(),
        "catalog_bytes": len(serialized), "release_inventory_sha256": payload_hash({"problem_ids": sorted(inventory)}),
        "crosswalk": crosswalk, "crosswalk_sha256": payload_hash(crosswalk_payload),
        "column_policy": POLICY, "column_policy_sha256": payload_hash(POLICY),
        "candidate_sha256": payload_hash({"candidates": [candidate.model_dump(mode="json") for candidate in candidates]}),
        "problem_rows": len(rows), "release_problems": len(inventory), "concept_columns": len(CONCEPTS),
        "missing_problems": 0, "extra_problems": 0,
        "concept_provenance": "One researcher's estimates; not instructor ground truth",
        "scope": "Format mapping and declared integrity only; source/use rights require external review"}
    return CatalogMapping(candidates, json.dumps(receipt, sort_keys=True, allow_nan=False))
