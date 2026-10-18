"""SQLite persistence for one synthetic replay learner."""

import os
import re
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from api.catalog import SEED_HISTORY


@contextmanager
def connect():
    path = Path(os.environ.get("PRACTICE_DB_PATH", ".data/demo.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize() -> None:
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS interactions (student_id TEXT NOT NULL, problem_id TEXT NOT NULL, sequence_index INTEGER NOT NULL, correct INTEGER NOT NULL CHECK(correct IN (0,1)), attempt_number INTEGER NOT NULL, PRIMARY KEY(student_id, sequence_index), UNIQUE(student_id, problem_id, attempt_number))")
        if db.execute("SELECT COUNT(*) FROM interactions").fetchone()[0] == 0:
            db.executemany("INSERT INTO interactions VALUES (?, ?, ?, ?, ?)", [("demo", row["problem_id"], index, int(row["correct"]), row["attempt_number"]) for index, row in enumerate(SEED_HISTORY)])


def canonical(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["correct"] = bool(result["correct"])
    return result


def history() -> list[dict]:
    initialize()
    with connect() as db:
        return [canonical(row) for row in db.execute("SELECT * FROM interactions WHERE student_id = 'demo' ORDER BY sequence_index")]


class ChoiceConflictError(ValueError):
    """A recorded choice already has a different simulated outcome."""


def _choice_attempt(db, choice_id, problem_id, correct):
    if choice_id is None:
        return None
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='recommendation_choices'").fetchone():
        raise LookupError("recommendation_choice_not_found")
    choice = db.execute("SELECT problem_id FROM recommendation_choices WHERE choice_id = ?", (choice_id,)).fetchone()
    if choice is None:
        raise LookupError("recommendation_choice_not_found")
    if choice["problem_id"] != problem_id:
        raise ValueError("choice_problem_mismatch")
    db.execute("CREATE TABLE IF NOT EXISTS recommendation_choice_attempts ("
               "choice_id TEXT PRIMARY KEY REFERENCES recommendation_choices(choice_id), "
               "student_id TEXT NOT NULL, sequence_index INTEGER NOT NULL, "
               "UNIQUE(student_id, sequence_index), "
               "FOREIGN KEY(student_id, sequence_index) REFERENCES interactions(student_id, sequence_index))")
    linked = db.execute("SELECT student_id, sequence_index FROM recommendation_choice_attempts WHERE choice_id = ?",
                        (choice_id,)).fetchone()
    if linked is None:
        return None
    row = db.execute("SELECT * FROM interactions WHERE student_id = ? AND sequence_index = ?",
                     (linked["student_id"], linked["sequence_index"])).fetchone()
    if row is None or row["problem_id"] != problem_id or row["student_id"] != "demo":
        raise ValueError("invalid_choice_attempt_link")
    if bool(row["correct"]) != correct:
        raise ChoiceConflictError("choice_outcome_conflict")
    return canonical(row)


def record(problem_id: str, correct: bool, *, choice_id: str | None = None) -> dict:
    if choice_id is not None and (not isinstance(choice_id, str) or not re.fullmatch(r"[a-f0-9]{32}", choice_id)):
        raise ValueError("Invalid choice ID")
    initialize()
    with connect() as db:
        # Context validation, numbering, interaction and link share one transaction.
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("BEGIN IMMEDIATE")
        existing = _choice_attempt(db, choice_id, problem_id, correct)
        if existing is not None:
            return existing
        sequence = db.execute("SELECT COALESCE(MAX(sequence_index), -1) + 1 FROM interactions WHERE student_id = 'demo'").fetchone()[0]
        attempt = db.execute("SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM interactions WHERE student_id = 'demo' AND problem_id = ?", (problem_id,)).fetchone()[0]
        db.execute("INSERT INTO interactions VALUES ('demo', ?, ?, ?, ?)", (problem_id, sequence, int(correct), attempt))
        if choice_id is not None:
            db.execute("INSERT INTO recommendation_choice_attempts VALUES (?, 'demo', ?)", (choice_id, sequence))
    return {"student_id": "demo", "problem_id": problem_id, "sequence_index": sequence, "correct": correct, "attempt_number": attempt}
