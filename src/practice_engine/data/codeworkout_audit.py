"""Read-only aggregate structural checks; no history reconstruction or data export."""

import argparse
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
from pathlib import Path

MAIN = frozenset({"EventID", "SubjectID", "AssignmentID", "ProblemID", "ServerTimestamp",
                  "EventType", "Score", "CodeStateID"})
CODE = frozenset({"CodeStateID", "Code"})
EVENTS = ("Run.Program", "Compile", "Compile.Error")


def _digest(stream):
    stream.seek(0)
    digest, size = sha256(), 0
    while chunk := stream.read(65536):
        digest.update(chunk)
        size += len(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def _scan(path, required, selected, visit):
    with path.open("rb") as binary:
        before = _digest(binary)
        binary.seek(0)
        text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
        try:
            reader = csv.reader(text, strict=True)
            headers = next(reader, [])
            counts = Counter(headers)
            available = {key: headers.index(key) for key in selected if counts[key] == 1}
            extra = [key for key in headers if key not in required]
            report = {"required_header_unique": {key: counts[key] == 1 for key in sorted(required)},
                "missing_required_headers": sum(counts[key] == 0 for key in required),
                "duplicate_header_excess": sum(count - 1 for count in counts.values()),
                "extra_header_columns": len(extra), "duplicate_extra_header_excess": len(extra) - len(set(extra)),
                "rows": 0, "malformed_rows": 0}
            for row in reader:
                report["rows"] += 1
                if len(row) != len(headers):
                    report["malformed_rows"] += 1
                    continue
                visit({key: row[index] for key, index in available.items()})
        finally:
            text.detach()
        if before != _digest(binary):
            raise ValueError("Source changed during structural audit")
    return {**before, **report}


def audit_structure(release_dir: Path) -> dict:
    """Audit exactly two known tables. Unknown names/values never enter output."""
    codes, events = set(), set()
    code_counts = {"empty_code_ids": 0, "duplicate_code_ids": 0}
    main_counts = {"empty_event_ids": 0, "duplicate_event_ids": 0,
        "run_missing_identity_keys": 0, "run_ambiguous_composite_keys": 0,
        "run_empty_code_ids": 0, "run_unresolved_code_ids": 0}
    event_counts = {**dict.fromkeys(EVENTS, 0), "other": 0, "empty": 0}
    scores = {"missing": 0, "invalid": 0, "finite_in_range": 0}

    def code_row(row):
        if "CodeStateID" not in row:
            return
        key = row["CodeStateID"]
        if not key.strip():
            code_counts["empty_code_ids"] += 1
        elif key in codes:
            code_counts["duplicate_code_ids"] += 1
        else:
            codes.add(key)

    code = _scan(release_dir / "CodeStates/CodeStates.csv", CODE, {"CodeStateID"}, code_row)

    def main_row(row):
        if "EventID" in row:
            key = row["EventID"]
            if not key.strip():
                main_counts["empty_event_ids"] += 1
            elif key in events:
                main_counts["duplicate_event_ids"] += 1
            else:
                events.add(key)
        if "EventType" not in row:
            return
        kind = row["EventType"]
        event_counts[kind if kind in EVENTS else "empty" if not kind.strip() else "other"] += 1
        if kind != "Run.Program":
            return
        if all(key in row for key in ("SubjectID", "AssignmentID", "ProblemID")):
            main_counts["run_missing_identity_keys"] += any(not row[key].strip() for key in ("SubjectID", "AssignmentID", "ProblemID"))
        if all(key in row for key in ("AssignmentID", "ProblemID")):
            main_counts["run_ambiguous_composite_keys"] += any(":" in row[key] for key in ("AssignmentID", "ProblemID"))
        if "CodeStateID" in row:
            key = row["CodeStateID"]
            main_counts["run_empty_code_ids"] += not key
            if code["required_header_unique"]["CodeStateID"]:
                main_counts["run_unresolved_code_ids"] += bool(key) and key not in codes
        if "Score" in row:
            value = row["Score"]
            if not value.strip():
                scores["missing"] += 1
            else:
                try:
                    score = Decimal(value)
                    valid = score.is_finite() and 0 <= score <= 1
                except InvalidOperation:
                    valid = False
                scores["finite_in_range" if valid else "invalid"] += 1

    main = _scan(release_dir / "MainTable.csv", MAIN, MAIN - {"ServerTimestamp"}, main_row)
    fields = main["required_header_unique"]
    usable = lambda *keys: all(fields[key] for key in keys)
    dependencies = {"empty_event_ids": usable("EventID"), "duplicate_event_ids": usable("EventID"),
        "run_missing_identity_keys": usable("EventType", "SubjectID", "AssignmentID", "ProblemID"),
        "run_ambiguous_composite_keys": usable("EventType", "AssignmentID", "ProblemID"),
        "run_empty_code_ids": usable("EventType", "CodeStateID"),
        "run_unresolved_code_ids": usable("EventType", "CodeStateID") and code["required_header_unique"]["CodeStateID"] and not code["malformed_rows"]}
    return {"audit_version": "codeworkout-structure-v1", "tables": {"MainTable.csv": main, "CodeStates/CodeStates.csv": code},
        "code_diagnostics": {key: value if code["required_header_unique"]["CodeStateID"] else None for key, value in code_counts.items()},
        "main_diagnostics": {key: value if dependencies[key] else None for key, value in main_counts.items()},
        "event_type_counts": event_counts if usable("EventType") else None,
        "run_score_validity": scores if usable("EventType", "Score") else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_dir", type=Path)
    args = parser.parse_args()
    try:
        report = audit_structure(args.release_dir)
    except (OSError, UnicodeError, csv.Error, ValueError):
        parser.error("Structural audit failed; inspect the private source and encoding locally.")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
