"""Synthetic replay requests remain safe after an ambiguous HTTP response."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sqlite3

from fastapi.testclient import TestClient
import pytest

from api import storage
from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PRACTICE_DB_PATH", str(tmp_path / "replay.sqlite3"))
    with TestClient(app) as api:
        yield api


def body(**updates):
    return {"student_id": "demo", "problem_id": "java-count", "correct": True,
            "request_id": "a" * 32, **updates}


def test_identical_retry_returns_original_receipt_after_other_interactions(client):
    before = client.get("/students/demo/history").json()
    first = client.post("/attempts", json=body())
    assert first.status_code == 201
    client.post("/attempts", json={"student_id": "demo", "problem_id": "java-count", "correct": False})
    with TestClient(app) as reopened:
        retry = reopened.post("/attempts", json=body())
    assert retry.status_code == 201 and retry.json() == first.json()
    assert len(client.get("/students/demo/history").json()) == len(before) + 2


@pytest.mark.parametrize("updates", [
    {"problem_id": "java-find"}, {"problem_id": "not-in-catalog"},
    {"correct": False}, {"choice_id": "b" * 32},
])
def test_reused_request_id_with_changed_payload_conflicts(client, updates):
    assert client.post("/attempts", json=body()).status_code == 201
    before = client.get("/students/demo/history").json()
    response = client.post("/attempts", json=body(**updates))
    assert response.status_code == 409
    assert response.json() == {"detail": "attempt_request_conflict"}
    assert client.get("/students/demo/history").json() == before


@pytest.mark.parametrize("request_id", [True, 1, "A" * 32, "short", "a" * 33])
def test_request_id_is_strict_lowercase_hex(client, request_id):
    before = client.get("/students/demo/history").json()
    assert client.post("/attempts", json=body(request_id=request_id)).status_code == 422
    assert client.get("/students/demo/history").json() == before


def test_simultaneous_identical_requests_append_one_interaction(client):
    before = client.get("/students/demo/history").json()
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post("/attempts", json=body()), range(8)))
    assert all(response.status_code == 201 for response in responses)
    assert all(response.json() == responses[0].json() for response in responses)
    assert len(client.get("/students/demo/history").json()) == len(before) + 1


def test_receipt_write_failure_rolls_back_interaction(client, monkeypatch):
    before = client.get("/students/demo/history").json()
    original = storage.connect

    @contextmanager
    def failing_connection():
        with original() as db:
            class Proxy:
                def execute(self, sql, parameters=()):
                    if sql.startswith("INSERT INTO attempt_request_receipts"):
                        raise sqlite3.OperationalError("synthetic receipt write failure")
                    return db.execute(sql, parameters)

                def __getattr__(self, name):
                    return getattr(db, name)
            yield Proxy()

    with monkeypatch.context() as patch:
        patch.setattr(storage, "connect", failing_connection)
        with pytest.raises(sqlite3.OperationalError):
            storage.record("java-count", True, request_id="a" * 32)
    assert client.get("/students/demo/history").json() == before
    saved = client.post("/attempts", json=body()).json()
    assert saved["sequence_index"] == before[-1]["sequence_index"] + 1


def test_existing_choice_link_accepts_distinct_request_id_without_duplicate(client):
    ranking = client.get("/students/demo/recommendations").json()
    problem = ranking["recommendations"][0]["problem_id"]
    choice = client.post("/recommendation-choices", json={
        "snapshot_id": ranking["snapshot_id"], "problem_id": problem}).json()
    first = client.post("/attempts", json=body(problem_id=problem, choice_id=choice["choice_id"]))
    assert first.status_code == 201
    retry = client.post("/attempts", json=body(problem_id=problem, choice_id=choice["choice_id"],
                                               request_id="c" * 32))
    assert retry.status_code == 201 and retry.json() == first.json()
    assert client.post("/attempts", json=body(problem_id=problem, choice_id=choice["choice_id"],
                                               request_id="c" * 32)).json() == first.json()
