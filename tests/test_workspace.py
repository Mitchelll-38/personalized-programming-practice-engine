"""A workspace response binds every history-dependent view to one read."""

from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest

from api import storage
from api.main import app
from api.recommendation_records import get_snapshot, list_snapshots


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PRACTICE_DB_PATH", str(tmp_path / "replay.sqlite3"))
    with TestClient(app) as api:
        yield api


def test_workspace_matches_existing_endpoints_and_persists_its_ranking(client):
    response = client.get("/students/demo/workspace")
    assert response.status_code == 200
    view = response.json()
    assert set(view) == {"model", "exercises", "history", "profile", "ranking"}
    assert view["model"] == client.get("/models/current").json()
    assert view["exercises"] == client.get("/exercises").json()
    assert view["history"] == client.get("/students/demo/history").json()
    assert view["profile"] == client.get("/students/demo/profile").json()
    later_ranking = client.get("/students/demo/recommendations").json()
    assert view["ranking"] == {**later_ranking, "snapshot_id": view["ranking"]["snapshot_id"]}

    saved = get_snapshot(view["ranking"]["snapshot_id"])
    assert saved.snapshot.history_sequence_index == view["history"][-1]["sequence_index"]
    assert [row.model_dump() for row in saved.snapshot.candidates] == [
        {key: row[key] for key in ("problem_id", "predicted_correctness", "score")}
        for row in view["ranking"]["recommendations"]]


def test_outcome_interleaved_after_history_read_cannot_mix_workspace_views(client, monkeypatch):
    from api import main

    original_read = storage.history
    original_record = main.record_snapshot
    reads = []
    inserted = []

    def read_once():
        observed = original_read()
        reads.append(observed)
        return observed

    def record_after_new_outcome(snapshot):
        inserted.append(storage.record("java-reverse", False))
        return original_record(snapshot)

    with monkeypatch.context() as patch:
        patch.setattr(main.storage, "history", read_once)
        patch.setattr(main, "record_snapshot", record_after_new_outcome)
        response = client.get("/students/demo/workspace")

    assert response.status_code == 200
    view = response.json()
    assert len(reads) == len(inserted) == 1
    assert view["history"] == reads[0]
    assert view["profile"]["total_interactions"] == len(view["history"]) == 4
    old_strings = next(row for row in view["profile"]["concepts"] if row["concept_id"] == "strings")
    assert old_strings["supporting_attempts"] == 0
    assert view["ranking"]["history_sequence_index"] == view["history"][-1]["sequence_index"] == 3
    assert get_snapshot(view["ranking"]["snapshot_id"]).snapshot.history_sequence_index == 3
    assert inserted[0]["sequence_index"] == 4

    refreshed = client.get("/students/demo/workspace").json()
    assert refreshed["history"][-1] == inserted[0]
    assert refreshed["profile"]["total_interactions"] == 5
    assert refreshed["ranking"]["history_sequence_index"] == 4
    new_strings = next(row for row in refreshed["profile"]["concepts"] if row["concept_id"] == "strings")
    assert new_strings["supporting_attempts"] == 1
    old_predictions = {row["problem_id"]: row["predicted_correctness"] for row in view["ranking"]["recommendations"]}
    new_predictions = {row["problem_id"]: row["predicted_correctness"] for row in refreshed["ranking"]["recommendations"]}
    assert old_predictions["java-reverse"] != new_predictions["java-reverse"]


def test_invalid_optional_policy_keeps_coherent_replay_without_a_ranking(client, tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    monkeypatch.setenv("PRACTICE_POLICY_CONFIG", str(policy_path))
    response = client.get("/students/demo/workspace")
    assert response.status_code == 200
    view = response.json()
    assert set(view) == {"model", "exercises", "history", "profile", "ranking", "ranking_error"}
    assert view["ranking"] is None and view["ranking_error"] == "practice_policy_unavailable"
    assert view["profile"]["total_interactions"] == len(view["history"]) == 4
    assert view["model"]["is_demo"] is True and len(view["exercises"]) == 8
    assert list_snapshots() == []
    assert client.get("/students/demo/recommendations").status_code == 503

    saved = client.post("/attempts", json={"student_id": "demo", "problem_id": "java-reverse", "correct": False})
    assert saved.status_code == 201
    refreshed = client.get("/students/demo/workspace").json()
    assert refreshed["ranking"] is None and refreshed["history"][-1] == saved.json()
    assert refreshed["profile"]["total_interactions"] == 5
    assert list_snapshots() == []

    policy_path.write_text('{"challenge_lower": 0.3, "challenge_upper": 0.5}')
    restored = client.get("/students/demo/workspace").json()
    assert "ranking_error" not in restored
    assert restored["ranking"]["history_sequence_index"] == saved.json()["sequence_index"]
    assert get_snapshot(restored["ranking"]["snapshot_id"]) is not None


def test_other_policy_failures_still_fail_workspace(client, monkeypatch):
    def unavailable():
        raise HTTPException(status_code=503, detail="different_failure")
    monkeypatch.setattr("api.main.configured_policy", unavailable)
    response = client.get("/students/demo/workspace")
    assert response.status_code == 503 and response.json() == {"detail": "different_failure"}
    assert list_snapshots() == []
