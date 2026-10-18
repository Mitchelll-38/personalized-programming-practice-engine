"""Project trusted local release CSVs into unresolved label-free chronology audits."""

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path

from .chronology_audit import ChronologyEvent, audit_chronology

PROJECTION = {"SubjectID": "subject_id", "AssignmentID": "assignment_id",
    "ProblemID": "problem_id", "EventType": "event_type", "ServerTimestamp": "timestamp",
    "ServerTimezone": "timezone", "Order": "order"}
METADATA = frozenset({"Version", "IsEventOrderingConsistent", "EventOrderScope", "EventOrderScopeColumns"})
SCOPE = frozenset({"SubjectID", "AssignmentID", "ProblemID"})
MAX_BYTES = 64 * 1024 * 1024
MAX_EVENTS = 250000
MAX_METADATA = 100


def _digest(stream):
    stream.seek(0)
    digest, count = sha256(), 0
    while chunk := stream.read(65536):
        count += len(chunk)
        if count > MAX_BYTES:
            raise ValueError("CSV byte cap exceeded")
        digest.update(chunk)
    return {"bytes": count, "sha256": digest.hexdigest()}


def _scan(path, selected, limit, visit, *, exact_headers=False):
    with path.open("rb") as binary:
        before = _digest(binary)
        binary.seek(0)
        text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
        count = 0
        try:
            reader = csv.reader(text, strict=True)
            headers = next(reader, [])
            if (len(headers) != len(set(headers)) or not set(selected).issubset(headers)
                    or (exact_headers and set(headers) != set(selected))):
                raise ValueError("Missing or ambiguous CSV headers")
            positions = {key: headers.index(key) for key in selected}
            for row in reader:
                count += 1
                if count > limit:
                    raise ValueError("CSV row cap exceeded")
                if len(row) != len(headers):
                    raise ValueError("Malformed CSV record")
                visit({key: row[index] for key, index in positions.items()})
        finally:
            text.detach()
        if before != _digest(binary):
            raise ValueError("CSV changed during audit")
    return {**before, "rows": count}


def audit_release_chronology(release_dir: Path) -> dict:
    """Return fixed aggregate fields; never interpret timezone or resolve chronology."""
    metadata, properties = {}, set()

    def metadata_row(row):
        key = row["Property"]
        if not key.strip() or key in properties:
            raise ValueError("Missing or duplicate metadata property")
        properties.add(key)
        if key in METADATA:
            metadata[key] = row["Value"]

    metadata_table = _scan(release_dir / "DatasetMetadata.csv", ("Property", "Value"),
                           MAX_METADATA, metadata_row, exact_headers=True)
    if not METADATA.issubset(metadata):
        raise ValueError("Missing required metadata")
    scope = metadata["EventOrderScopeColumns"].split(";")
    booleans = {"TRUE": True, "FALSE": False, "true": True, "false": False, "True": True, "False": False}
    if (metadata["Version"] != "6" or metadata["EventOrderScope"] != "Restricted"
            or len(scope) != len(SCOPE) or set(scope) != SCOPE
            or metadata["IsEventOrderingConsistent"] not in booleans):
        raise ValueError("Unsupported dataset metadata")
    events = []

    def project(row):
        events.append(ChronologyEvent(**{target: row[source] for source, target in PROJECTION.items()}))

    main_table = _scan(release_dir / "MainTable.csv", PROJECTION, MAX_EVENTS, project)
    result = audit_chronology(events)
    return {"adapter_version": "chronology-csv-v1",
        "tables": {"MainTable.csv": main_table, "DatasetMetadata.csv": metadata_table},
        "declared_metadata": {"version": 6, "is_event_ordering_consistent": booleans[metadata["IsEventOrderingConsistent"]],
            "event_order_scope": "Restricted", "event_order_scope_columns": scope},
        "chronology": result.aggregates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_dir", type=Path)
    args = parser.parse_args()
    try:
        result = audit_release_chronology(args.release_dir)
    except (OSError, UnicodeError, csv.Error, ValueError):
        parser.error("Chronology CSV audit failed; inspect the private source, metadata and caps locally.")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
