import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from practice_engine.data.codeworkout_audit import CODE, MAIN, audit_structure, main


def table(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def event(**update):
    return {"EventID": "synthetic-event-secret", "SubjectID": "synthetic-student-secret",
        "AssignmentID": "synthetic-assignment-secret", "ProblemID": "synthetic-problem-secret",
        "ServerTimestamp": "intentionally-not-a-timestamp", "EventType": "Run.Program",
        "Score": "0.75", "CodeStateID": "synthetic-state-secret", **update}


@pytest.fixture
def release(tmp_path):
    write_main(tmp_path, [event()])
    table(tmp_path / "CodeStates/CodeStates.csv", sorted(CODE), [["private multiline\ncode", "synthetic-state-secret"]])
    return tmp_path


def write_main(path, rows, headers=None):
    headers = sorted(MAIN) if headers is None else headers
    table(path / "MainTable.csv", headers, [[row.get(key, "") for key in headers] for row in rows])


def test_hashes_aggregate_only_exact_known_tables_without_touching_other_data(release, monkeypatch):
    for name in ("early.csv", "late.csv", "LinkTables/Subject.csv"):
        path = release / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"\xffprivate-unrelated-table")
    before = {path: path.read_bytes() for path in release.rglob("*") if path.is_file()}
    opened = []
    original = Path.open
    def tracked(path, *args, **kwargs):
        opened.append(path.relative_to(release).as_posix())
        return original(path, *args, **kwargs)
    with monkeypatch.context() as context:
        context.setattr(Path, "open", tracked)
        result = audit_structure(release)
    assert opened == ["CodeStates/CodeStates.csv", "MainTable.csv"]
    for name, value in result["tables"].items():
        assert value["sha256"] == sha256(before[release / name]).hexdigest()
        assert value["bytes"] == len(before[release / name]) and value["rows"] == 1
        assert all(value["required_header_unique"].values()) and value["malformed_rows"] == 0
    assert result["run_score_validity"] == {"missing": 0, "invalid": 0, "finite_in_range": 1}
    assert not any(result["main_diagnostics"].values()) and not any(result["code_diagnostics"].values())
    assert {path: path.read_bytes() for path in before} == before
    text = json.dumps(result)
    for secret in (*event().values(), "private multiline", str(release), "grade"):
        if secret != "Run.Program":
            assert secret not in text
    assert set(result) == {"audit_version", "tables", "code_diagnostics", "main_diagnostics", "event_type_counts", "run_score_validity"}


def test_unknown_headers_and_event_values_are_counts_never_echoed(release):
    write_main(release, [event(EventType="private-unknown-event"), event(EventType=""), event(EventType="Compile")],
               [*sorted(MAIN), "private-unknown-header", "private-unknown-header"])
    result = audit_structure(release)
    assert result["event_type_counts"] == {"Run.Program": 0, "Compile": 1, "Compile.Error": 0, "empty": 1, "other": 1}
    assert result["tables"]["MainTable.csv"]["extra_header_columns"] == 2
    assert result["tables"]["MainTable.csv"]["duplicate_extra_header_excess"] == 1
    assert "private-unknown" not in json.dumps(result)


@pytest.mark.parametrize("duplicate", [False, True])
def test_unavailable_score_columns_are_null_not_zero(release, duplicate):
    headers = [key for key in sorted(MAIN) if key != "Score"] + (["Score", "Score"] if duplicate else [])
    write_main(release, [event()], headers)
    result = audit_structure(release)
    assert result["run_score_validity"] is None
    assert result["event_type_counts"]["Run.Program"] == 1
    assert result["tables"]["MainTable.csv"]["required_header_unique"]["Score"] is False


def test_missing_subject_does_not_hide_auditable_composite_ambiguity(release):
    write_main(release, [event(AssignmentID="ambiguous:assignment")], sorted(MAIN - {"SubjectID"}))
    result = audit_structure(release)
    assert result["main_diagnostics"]["run_missing_identity_keys"] is None
    assert result["main_diagnostics"]["run_ambiguous_composite_keys"] == 1


@pytest.mark.parametrize("missing", ["code-id", "event-type", "duplicate-event-id"])
def test_other_unavailable_columns_never_claim_success(release, missing):
    if missing == "code-id":
        table(release / "CodeStates/CodeStates.csv", ["Code"], [["private code"]])
    elif missing == "event-type":
        write_main(release, [event()], sorted(MAIN - {"EventType"}))
    else:
        write_main(release, [event()], [*sorted(MAIN), "EventID"])
    result = audit_structure(release)
    if missing == "code-id":
        assert all(value is None for value in result["code_diagnostics"].values())
        assert result["main_diagnostics"]["run_unresolved_code_ids"] is None
        assert result["main_diagnostics"]["run_empty_code_ids"] == 0
    elif missing == "event-type":
        assert result["event_type_counts"] is None and result["run_score_validity"] is None
        assert result["main_diagnostics"]["run_missing_identity_keys"] is None
    else:
        assert result["main_diagnostics"]["empty_event_ids"] is None
        assert result["main_diagnostics"]["duplicate_event_ids"] is None


def test_malformed_rows_and_code_table_gap_do_not_claim_join_success(release):
    with (release / "MainTable.csv").open("a", newline="") as stream:
        csv.writer(stream).writerows([["too-short"], list(event().values()) + ["extra"]])
    table(release / "CodeStates/CodeStates.csv", sorted(CODE), [["malformed"]])
    result = audit_structure(release)
    assert result["tables"]["MainTable.csv"]["rows"] == 3
    assert result["tables"]["MainTable.csv"]["malformed_rows"] == 2
    assert result["main_diagnostics"]["run_unresolved_code_ids"] is None
    assert result["run_score_validity"]["finite_in_range"] == 1


@pytest.mark.parametrize("score,category", [("", "missing"), ("NaN", "invalid"), ("Infinity", "invalid"),
    ("-0.1", "invalid"), ("1.01", "invalid"), ("nonsense", "invalid"), ("0", "finite_in_range"), ("1", "finite_in_range")])
def test_run_score_validity_without_label_or_distribution_output(release, score, category):
    write_main(release, [event(Score=score), event(EventID="compile-event", EventType="Compile", Score="not-a-grade")])
    result = audit_structure(release)
    assert result["run_score_validity"][category] == 1 and sum(result["run_score_validity"].values()) == 1


def test_duplicate_ids_missing_keys_and_code_join_diagnostics(release):
    table(release / "CodeStates/CodeStates.csv", sorted(CODE), [["code", "state"], ["other", "state"], ["", ""]])
    write_main(release, [event(CodeStateID="state"), event(SubjectID="", AssignmentID="bad:key", CodeStateID=""),
        event(EventID="", CodeStateID="unresolved")])
    result = audit_structure(release)
    assert result["code_diagnostics"] == {"empty_code_ids": 1, "duplicate_code_ids": 1}
    assert result["main_diagnostics"] == {"empty_event_ids": 1, "duplicate_event_ids": 1,
        "run_missing_identity_keys": 1, "run_ambiguous_composite_keys": 1, "run_empty_code_ids": 1, "run_unresolved_code_ids": 1}


def test_source_mutation_rejected(release, monkeypatch):
    from practice_engine.data import codeworkout_audit as module
    original = module._digest
    calls = 0
    def changing(stream):
        nonlocal calls
        result = original(stream)
        calls += 1
        if calls == 1:
            with Path(stream.name).open("ab") as changed:
                changed.write(b"\nsynthetic appended,tail\n")
        return result
    monkeypatch.setattr(module, "_digest", changing)
    with pytest.raises(ValueError, match="changed"):
        audit_structure(release)


def test_cli_complete_receipt_and_safe_parse_failure(release, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["audit", str(release)])
    main()
    assert json.loads(capsys.readouterr().out)["audit_version"] == "codeworkout-structure-v1"
    (release / "MainTable.csv").write_text('"unterminated', encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main()
    output = capsys.readouterr()
    assert error.value.code == 2 and output.out == "" and str(release) not in output.err and "Traceback" not in output.err
