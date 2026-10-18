import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from practice_engine.data import chronology_csv as module
from practice_engine.data.chronology_audit import ChronologyEvent, audit_chronology

HEADERS = ["SubjectID", "AssignmentID", "ProblemID", "EventType", "ServerTimestamp", "ServerTimezone", "Order", "Score", "Code"]
DECLARATION = {"Version": "6", "IsEventOrderingConsistent": "TRUE", "EventOrderScope": "Restricted",
               "EventOrderScopeColumns": "SubjectID;AssignmentID;ProblemID"}
ROWS = [["private-subject", "private-assignment", "private-problem", "Run.Program", "2020-01-01T12:00:00", "0", "0", "private-outcome", "private-code"],
        ["private-subject", "private-assignment", "private-problem", "Run.Program", "2020-01-01T12:00:00", "UTC", "1", "private-outcome", "private-code"]]


def write(path, headers, rows):
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


@pytest.fixture
def release(tmp_path):
    write(tmp_path / "DatasetMetadata.csv", ["Property", "Value"], DECLARATION.items())
    write(tmp_path / "MainTable.csv", HEADERS, ROWS)
    return tmp_path


def test_exact_projection_pure_parity_hashes_and_no_unrelated_reads(release, monkeypatch):
    for name in ("CodeStates/CodeStates.csv", "LinkTables/Subject.csv", "early.csv", "late.csv"):
        path = release / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(b"\xffprivate-unrelated-input")
    before = {path: path.read_bytes() for path in release.rglob("*") if path.is_file()}
    opened = []
    original = Path.open
    def tracked(path, *args, **kwargs):
        opened.append(path.relative_to(release).as_posix())
        return original(path, *args, **kwargs)
    with monkeypatch.context() as context:
        context.setattr(Path, "open", tracked)
        result = module.audit_release_chronology(release)
    expected = [ChronologyEvent("private-subject", "private-assignment", "private-problem", "Run.Program",
                               "2020-01-01T12:00:00", zone, str(index)) for index, zone in enumerate(("0", "UTC"))]
    assert result["chronology"] == audit_chronology(expected).aggregates
    assert opened == ["DatasetMetadata.csv", "MainTable.csv"]
    for name, receipt in result["tables"].items():
        assert receipt["bytes"] == len(before[release / name])
        assert receipt["sha256"] == sha256(before[release / name]).hexdigest()
    assert result["tables"]["MainTable.csv"]["rows"] == 2
    assert result["chronology"]["normalization_applied"] is False
    assert "private-" not in json.dumps(result) and str(release) not in json.dumps(result)
    assert {path: path.read_bytes() for path in before} == before


def test_outcome_code_and_unknown_metadata_changes_do_not_change_aggregates(release):
    before = module.audit_release_chronology(release)
    write(release / "MainTable.csv", HEADERS, [row[:-2] + ["a different outcome", "arbitrary\nsource code"] for row in ROWS])
    write(release / "DatasetMetadata.csv", ["Property", "Value"], [*DECLARATION.items(), ("unknown-private-key", "unknown-private-value")])
    after = module.audit_release_chronology(release)
    assert after["chronology"] == before["chronology"]
    assert after["declared_metadata"] == before["declared_metadata"]
    assert after["tables"] != before["tables"] and "unknown-private" not in json.dumps(after)


@pytest.mark.parametrize("property,value", [("Version", "5"), ("Version", "6.0"),
    ("IsEventOrderingConsistent", "not-a-boolean"), ("EventOrderScope", "Global"),
    ("EventOrderScopeColumns", "SubjectID;ProblemID"), ("EventOrderScopeColumns", "SubjectID;ProblemID;ProblemID")])
def test_unsupported_metadata_fails_without_echoing_values(release, property, value):
    write(release / "DatasetMetadata.csv", ["Property", "Value"], {**DECLARATION, property: value}.items())
    with pytest.raises(ValueError, match="Unsupported dataset metadata"):
        module.audit_release_chronology(release)


def test_false_consistency_is_declaration_not_chronology_approval(release):
    write(release / "DatasetMetadata.csv", ["Property", "Value"], {**DECLARATION, "IsEventOrderingConsistent": "FALSE",
        "EventOrderScopeColumns": "ProblemID;SubjectID;AssignmentID"}.items())
    result = module.audit_release_chronology(release)
    assert result["declared_metadata"]["is_event_ordering_consistent"] is False
    assert result["chronology"]["global_timeline_verified"] is False
    assert result["chronology"]["interpretation_status"] == "unresolved"


@pytest.mark.parametrize("kind", ["missing-property", "duplicate-property", "duplicate-unknown-property", "extra-metadata-header", "missing-projection", "duplicate-projection", "malformed-main"])
def test_missing_ambiguous_or_malformed_csv_fails(release, kind):
    if kind == "missing-property":
        write(release / "DatasetMetadata.csv", ["Property", "Value"], [(key, value) for key, value in DECLARATION.items() if key != "Version"])
    elif "property" in kind:
        rows = [*DECLARATION.items(), ("Version", "6")] if kind == "duplicate-property" else [*DECLARATION.items(), ("private", "a"), ("private", "b")]
        write(release / "DatasetMetadata.csv", ["Property", "Value"], rows)
    elif kind == "extra-metadata-header":
        write(release / "DatasetMetadata.csv", ["Property", "Value", "private-extra"], [])
    elif kind == "missing-projection":
        write(release / "MainTable.csv", HEADERS[1:], [row[1:] for row in ROWS])
    elif kind == "duplicate-projection":
        write(release / "MainTable.csv", [*HEADERS, "Order"], [row + ["1"] for row in ROWS])
    else:
        write(release / "MainTable.csv", HEADERS, [ROWS[0][:-1]])
    with pytest.raises(ValueError):
        module.audit_release_chronology(release)


def test_caps_and_source_mutation_fail_before_receipt(release, monkeypatch):
    for name, limit in (("MAX_BYTES", 1), ("MAX_EVENTS", 1), ("MAX_METADATA", 1)):
        with monkeypatch.context() as context:
            context.setattr(module, name, limit)
            with pytest.raises(ValueError, match="cap exceeded"):
                module.audit_release_chronology(release)
    original = module._digest
    calls = 0
    def mutate(stream):
        nonlocal calls
        result = original(stream)
        calls += 1
        if calls == 1:
            with Path(stream.name).open("ab") as changed:
                changed.write(b"another-property,another-value\n")
        return result
    monkeypatch.setattr(module, "_digest", mutate)
    with pytest.raises(ValueError, match="changed"):
        module.audit_release_chronology(release)


def test_cli_safe_complete_output_and_generic_private_failures(release, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chronology_csv", str(release)])
    module.main()
    assert json.loads(capsys.readouterr().out)["adapter_version"] == "chronology-csv-v1"
    (release / "MainTable.csv").write_text('"unterminated-private-value', encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        module.main()
    output = capsys.readouterr()
    assert error.value.code == 2 and output.out == ""
    assert "private-value" not in output.err and str(release) not in output.err and "Traceback" not in output.err
