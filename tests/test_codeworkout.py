import csv
import json
from pathlib import Path
import shutil

import pytest

from practice_engine.data.codeworkout import import_codeworkout
from practice_engine.data.pipeline import prediction_examples


FIXTURE = Path(__file__).parents[1] / "data/fixtures/codeworkout"


@pytest.fixture
def release(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / "release")
    return tmp_path / "release"


def rewrite(release, change):
    path = release / "MainTable.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    change(rows)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load(release):
    return import_codeworkout(release, release / "catalog.json")


def test_scored_runs_only_recomputed_attempts_and_causal_boundary(release):
    imported = load(release)
    student = [row for row in imported.rows if row.student_id == "synthetic-a"]
    assert [(r.problem_id, r.attempt_number, r.correct) for r in student] == [
        ("1:1", 1, False), ("1:1", 2, True), ("1:2", 1, True), ("2:1", 1, False)]
    assert imported.audit["non_submission_events_excluded"] == 2
    assert imported.audit["submissions_without_code"] == 3
    assert imported.audit["source_release_verified"] is False
    examples = prediction_examples(imported.rows)
    assert len(examples) == 5
    target = next(row for row in examples if row.candidate.problem_id == "1:2")
    assert len(target.history) == 1 and target.history[0].correct is False
    assert "submitted_code" not in target.candidate.model_dump()
    rewrite(release, lambda rows: rows.reverse())
    assert load(release) == imported


@pytest.mark.parametrize("score", ["", "NaN", "Infinity", "-0.1", "1.1", "unknown"])
def test_invalid_first_grade_never_promotes_later_retry(release, score):
    rewrite(release, lambda rows: rows[2].update(Score=score))
    with pytest.raises(ValueError, match="Score"):
        load(release)


@pytest.mark.parametrize("field,value,error", [
    ("EventID", "e4", "duplicate EventID"),
    ("ServerTimestamp", "2026-01-01T12:02:00Z", "timestamp tie"),
    ("ServerTimestamp", "unknown", "ServerTimestamp"),
    ("ServerTimestamp", "2026-01-01", "ServerTimestamp"),
    ("ServerTimestamp", "2026-01-01T12:00:01", "mixed timezone"),
    ("SubjectID", "", "submission key"),
    ("CodeStateID", "missing", "unresolved CodeStateID"),
    ("AssignmentID", "1:2", "ambiguous composite"),
])
def test_corrupt_submission_fails_closed(release, field, value, error):
    rewrite(release, lambda rows: rows[2].update({field: value}))
    with pytest.raises(ValueError, match=error):
        load(release)


@pytest.mark.parametrize("change", [
    lambda entries: entries.pop(),
    lambda entries: entries[0].update(problem_text=" "),
    lambda entries: entries[0].update(concept_ids=[]),
    lambda entries: entries.append(entries[0]),
])
def test_missing_or_ambiguous_catalog_not_fabricated(release, change):
    path = release / "catalog.json"
    entries = json.loads(path.read_text())
    change(entries)
    path.write_text(json.dumps(entries))
    with pytest.raises(ValueError, match="[Cc]atalog"):
        load(release)


def test_duplicate_code_state_and_missing_schema(release):
    with (release / "CodeStates/CodeStates.csv").open("a") as stream:
        stream.write("c1,return 3;\n")
    with pytest.raises(ValueError, match="duplicate CodeStateID"):
        load(release)
    (release / "MainTable.csv").write_text("SubjectID\nsynthetic-a\n")
    with pytest.raises(ValueError, match="missing columns"):
        load(release)
