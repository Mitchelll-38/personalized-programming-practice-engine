from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sqlite3

from fastapi.testclient import TestClient
import pytest

from api import storage
from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "demo.sqlite3"
    monkeypatch.setenv("PRACTICE_DB_PATH", str(path))
    with TestClient(app) as api:
        yield api, path


def linked_request(api):
    ranking = api.get("/students/demo/recommendations").json()
    problem = ranking["recommendations"][0]["problem_id"]
    choice = api.post("/recommendation-choices", json={"snapshot_id": ranking["snapshot_id"], "problem_id": problem})
    assert choice.status_code == 201
    return {"student_id": "demo", "problem_id": problem, "correct": True, "choice_id": choice.json()["choice_id"]}


def test_link_is_persisted_and_identical_retry_returns_original_even_after_later_attempt(client):
    api, path = client
    body = linked_request(api)
    before = api.get("/students/demo/history").json()
    response = api.post("/attempts", json=body)
    assert response.status_code == 201
    saved = response.json()
    assert saved["sequence_index"] == before[-1]["sequence_index"] + 1
    assert set(saved) == {"student_id", "problem_id", "sequence_index", "correct", "attempt_number"}
    api.post("/attempts", json={key: value for key, value in body.items() if key != "choice_id"})
    with TestClient(app) as reopened:
        assert reopened.post("/attempts", json=body).json() == saved
    after = api.get("/students/demo/history").json()
    assert len(after) == len(before) + 2
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM recommendation_choice_attempts").fetchall() == [
            (body["choice_id"], "demo", saved["sequence_index"])]


def test_conflicting_outcome_wrong_problem_and_unknown_choice_do_not_add_attempts(client):
    api, _ = client
    body = linked_request(api)
    before = api.get("/students/demo/history").json()
    assert api.post("/attempts", json={**body, "choice_id": "0" * 32}).status_code == 404
    other = "java-sum" if body["problem_id"] != "java-sum" else "java-even"
    assert api.post("/attempts", json={**body, "problem_id": other}).status_code == 422
    assert api.get("/students/demo/history").json() == before
    assert api.post("/attempts", json=body).status_code == 201
    after = api.get("/students/demo/history").json()
    response = api.post("/attempts", json={**body, "correct": False})
    assert response.status_code == 409 and response.json() == {"detail": "choice_outcome_conflict"}
    assert api.get("/students/demo/history").json() == after


@pytest.mark.parametrize("choice_id", [True, "bad", "' OR 1=1 --", 1])
def test_bad_choice_ids_rejected(client, choice_id):
    api, _ = client
    before = api.get("/students/demo/history").json()
    assert api.post("/attempts", json={"student_id": "demo", "problem_id": "java-count",
        "correct": True, "choice_id": choice_id}).status_code == 422
    assert api.get("/students/demo/history").json() == before


def test_unknown_choice_without_choice_schema_returns404_and_preserves_unlinked_retries(client):
    api, _ = client
    body = {"student_id": "demo", "problem_id": "java-count", "correct": False}
    assert api.post("/attempts", json={**body, "choice_id": "0" * 32}).status_code == 404
    first = api.post("/attempts", json=body).json()
    second = api.post("/attempts", json=body).json()
    assert second["sequence_index"] == first["sequence_index"] + 1
    assert second["attempt_number"] == first["attempt_number"] + 1


def test_simultaneous_identical_linked_requests_create_only_one_interaction(client):
    api, path = client
    body = linked_request(api)
    before = api.get("/students/demo/history").json()
    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(lambda _: api.post("/attempts", json=body), range(8)))
    assert all(row.status_code == 201 for row in responses)
    assert all(row.json() == responses[0].json() for row in responses)
    assert len(api.get("/students/demo/history").json()) == len(before) + 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM recommendation_choice_attempts").fetchone()[0] == 1


def test_link_insert_failure_rolls_back_interaction_and_numbering(client, monkeypatch):
    api, _ = client
    body = linked_request(api)
    before = storage.history()
    original = storage.connect
    @contextmanager
    def failing_connection():
        with original() as db:
            class Proxy:
                def execute(self, sql, parameters=()):
                    if sql.startswith("INSERT INTO recommendation_choice_attempts"):
                        raise sqlite3.OperationalError("synthetic link write failure")
                    return db.execute(sql, parameters)
                def __getattr__(self, key):
                    return getattr(db, key)
            yield Proxy()
    with monkeypatch.context() as patch:
        patch.setattr(storage, "connect", failing_connection)
        with pytest.raises(sqlite3.OperationalError):
            storage.record(body["problem_id"], True, choice_id=body["choice_id"])
    assert storage.history() == before
    saved = storage.record(body["problem_id"], True, choice_id=body["choice_id"])
    assert saved["sequence_index"] == before[-1]["sequence_index"] + 1
