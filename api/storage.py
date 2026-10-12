"""SQLite persistence for one synthetic replay learner."""

import os
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


def record(problem_id: str, correct: bool) -> dict:
    initialize()
    with connect() as db:
        # The transaction covers numbering and insertion, including simultaneous requests.
        db.execute("BEGIN IMMEDIATE")
        sequence = db.execute("SELECT COALESCE(MAX(sequence_index), -1) + 1 FROM interactions WHERE student_id = 'demo'").fetchone()[0]
        attempt = db.execute("SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM interactions WHERE student_id = 'demo' AND problem_id = ?", (problem_id,)).fetchone()[0]
        db.execute("INSERT INTO interactions VALUES ('demo', ?, ?, ?, ?)", (problem_id, sequence, int(correct), attempt))
    return {"student_id": "demo", "problem_id": problem_id, "sequence_index": sequence, "correct": correct, "attempt_number": attempt}
