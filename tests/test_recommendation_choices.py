from concurrent.futures import ThreadPoolExecutor
import sqlite3

from fastapi.testclient import TestClient
import pytest

from api.main import app
from api.recommendation_choices import ChoiceRequest, StoredChoice, record_choice
from api.recommendation_records import get_snapshot


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "demo.sqlite3"
    monkeypatch.setenv("PRACTICE_DB_PATH", str(path))
    with TestClient(app) as client:
        yield client, path


def context(client):
    body = client.get("/students/demo/recommendations").json()
    return {"snapshot_id": body["snapshot_id"], "problem_id": body["recommendations"][0]["problem_id"]}


def test_choice_persists_exact_context_without_changing_attempts_or_snapshot(client):
    api, path = client
    request = context(api)
    snapshot = get_snapshot(request["snapshot_id"])
    history = api.get("/students/demo/history").json()
    # A later outcome does not rewrite the earlier ranking's context.
    api.post("/attempts", json={"student_id": "demo", "problem_id": "java-reverse", "correct": False})
    response = api.post("/recommendation-choices", json=request)
    assert response.status_code == 201
    saved = StoredChoice.model_validate_json(response.content)
    assert saved.snapshot_id == request["snapshot_id"] and saved.problem_id == request["problem_id"]
    assert saved.created_at.utcoffset().total_seconds() == 0
    assert get_snapshot(request["snapshot_id"]) == snapshot
    assert api.get("/students/demo/history").json()[:-1] == history
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM recommendation_choices").fetchone() == (
            saved.choice_id, saved.created_at.isoformat(), saved.snapshot_id, saved.problem_id)
    with TestClient(app) as reopened:
        second = reopened.post("/recommendation-choices", json=request).json()
    assert second["choice_id"] != saved.choice_id
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM recommendation_choices").fetchone()[0] == 2


@pytest.mark.parametrize("change", [{"snapshot_id": "invalid"}, {"snapshot_id": True},
    {"problem_id": " "}, {"correct": True}, {"student_id": "real"},
    {"created_at": "2000-01-01T00:00:00Z"}, {"submitted_code": "return 1;"}])
def test_invalid_choice_schema_rejected_before_event_write(client, change):
    api, path = client
    assert api.post("/recommendation-choices", json={**context(api), **change}).status_code == 422
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='recommendation_choices'").fetchone() is None


def test_unknown_context_or_non_candidate_rejected_without_write(client):
    api, path = client
    request = context(api)
    assert api.post("/recommendation-choices", json={**request, "snapshot_id": "0" * 32}).status_code == 404
    assert api.post("/recommendation-choices", json={**request, "problem_id": "absent"}).status_code == 422
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='recommendation_choices'").fetchone() is None
    invalid = ChoiceRequest(**request).model_copy(update={"problem_id": " "})
    with pytest.raises(ValueError):
        record_choice(invalid)


def test_concurrent_explicit_choices_remain_separate_complete_records(client):
    api, path = client
    request = ChoiceRequest(**context(api))
    with ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(lambda _: record_choice(request), range(8)))
    assert len({row.choice_id for row in rows}) == 8
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM recommendation_choices WHERE snapshot_id=? AND problem_id=?",
                          (request.snapshot_id, request.problem_id)).fetchone()[0] == 8


def test_corrupt_snapshot_cannot_create_choice(client):
    api, path = client
    request = context(api)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE recommendation_snapshots SET payload_json='{}'")
    response = api.post("/recommendation-choices", json=request)
    assert response.status_code == 422 and response.json() == {"detail": "invalid_recommendation_choice"}
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='recommendation_choices'").fetchone() is None
