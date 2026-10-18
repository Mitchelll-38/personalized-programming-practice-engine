from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest

from api import storage
from api.recommendation_records import (
    RecommendationSnapshot, ScoredCandidate, get_snapshot, list_snapshots, record_snapshot,
)


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "demo.sqlite3"
    monkeypatch.setenv("PRACTICE_DB_PATH", str(path))
    return path


def snapshot():
    return RecommendationSnapshot(model_id="demo-history-v1", policy_version="demo-ranking-v1",
        dataset_version="synthetic-v1", history_sequence_index=3,
        candidates=(ScoredCandidate(problem_id="p2", predicted_correctness=.7, score=.9),
                    ScoredCandidate(problem_id="p1", predicted_correctness=.2, score=-.4)))


def test_additive_storage_preserves_interactions_and_reconstructs_order(database):
    before = storage.history()
    first, second = record_snapshot(snapshot()), record_snapshot(snapshot())
    assert first.snapshot_id != second.snapshot_id
    assert get_snapshot(first.snapshot_id) == first
    assert first.created_at.utcoffset().total_seconds() == 0
    assert [c.problem_id for c in get_snapshot(first.snapshot_id).snapshot.candidates] == ["p2", "p1"]
    assert list_snapshots(limit=1) == [second]
    assert len(list_snapshots()) == 2
    assert get_snapshot("0" * 32) is None
    assert storage.history() == before
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM interactions").fetchone()[0] == len(before)
    assert "correct" not in json.loads(first.model_dump_json())["snapshot"]["candidates"][0]


def test_concurrent_records_are_distinct_and_complete(database):
    with ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(lambda _: record_snapshot(snapshot()), range(8)))
    assert len({row.snapshot_id for row in rows}) == 8
    assert len(list_snapshots()) == 8
    assert all(get_snapshot(row.snapshot_id) == row for row in rows)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -.1, 1.1])
def test_bad_probabilities_rejected(value):
    with pytest.raises(ValueError):
        ScoredCandidate(problem_id="p", predicted_correctness=value, score=.5)


@pytest.mark.parametrize("change", [{"student_id": "real"}, {"source_kind": "unverified"},
    {"history_sequence_index": True}, {"calibrated": "false"}, {"correct": True},
    {"selected_problem_id": "p1"}, {"submitted_code": "code"}, {"candidates": ()}])
def test_invalid_or_outcome_snapshot_fields_rejected(change):
    with pytest.raises(ValueError):
        RecommendationSnapshot.model_validate({**snapshot().model_dump(), **change})


def test_duplicate_candidates_and_unchecked_copy_fail_before_writes(database):
    value = snapshot()
    broken = value.model_copy(update={"candidates": (value.candidates[0], value.candidates[0])})
    with pytest.raises(ValueError, match="distinct"):
        record_snapshot(broken)
    assert not database.exists()


@pytest.mark.parametrize("limit", [True, 0, 501, 1.5, "1"])
def test_read_limit_is_bounded(database, limit):
    with pytest.raises(ValueError):
        list_snapshots(limit=limit)
    assert not database.exists()


def test_invalid_ids_and_corrupt_payload_fail_closed(database):
    for identifier in ("' OR 1=1 --", True, "bad"):
        with pytest.raises(ValueError):
            get_snapshot(identifier)
    saved = record_snapshot(snapshot())
    with sqlite3.connect(database) as db:
        db.execute("UPDATE recommendation_snapshots SET payload_json = ? WHERE snapshot_id = ?",
                   ('{"unexpected":"corrupt"}', saved.snapshot_id))
    with pytest.raises(ValueError):
        get_snapshot(saved.snapshot_id)
