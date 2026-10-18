from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
import pytest

from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PRACTICE_DB_PATH", str(tmp_path / "replay.sqlite3"))
    with TestClient(app) as client:
        yield client


def test_catalog_model_and_seed_are_explicit_demo(client):
    assert client.get("/health").json() == {"status": "ok"}
    metadata = client.get("/models/current").json()
    assert metadata["is_demo"] is True and metadata["calibrated"] is False
    catalog = client.get("/exercises").json()
    assert len(catalog) == 8
    history = client.get("/students/demo/history").json()
    assert [row["sequence_index"] for row in history] == [0, 1, 2, 3]
    assert history[2]["attempt_number"] == 2


def test_replay_persists_and_retry_does_not_inflate_profile(client):
    before = client.get("/students/demo/profile").json()
    response = client.post("/attempts", json={"student_id": "demo", "problem_id": "java-even", "correct": True})
    assert response.status_code == 201
    assert response.json()["attempt_number"] == 3
    assert response.json()["sequence_index"] == 4
    after = client.get("/students/demo/profile").json()
    assert after["concepts"] == before["concepts"]
    assert after["first_attempts"] == before["first_attempts"] == 3
    assert after["total_interactions"] == before["total_interactions"] + 1 == 5
    assert after["retries"] == before["retries"] + 1 == 2
    with TestClient(app) as another_client:
        assert another_client.get("/students/demo/history").json()[-1] == response.json()


def test_predict_uses_only_supplied_history_and_preserves_candidate_order(client):
    body = {"history": [], "candidate_ids": ["java-reverse", "java-sum"]}
    response = client.post("/predict", json=body)
    assert response.status_code == 200
    assert response.json()["predictions"] == [{"problem_id": "java-reverse", "predicted_correctness": 0.5}, {"problem_id": "java-sum", "predicted_correctness": 0.5}]
    body["history"] = [{"problem_id": "java-sum", "sequence_index": 0, "correct": True, "attempt_number": 1}]
    assert client.post("/predict", json=body).json()["predictions"][1]["predicted_correctness"] == pytest.approx(2 / 3, abs=1e-6)


@pytest.mark.parametrize("extra", ["correct", "target_correct", "candidate_correctness"])
def test_predict_rejects_target_fields(client, extra):
    assert client.post("/predict", json={"history": [], "candidate_ids": ["java-sum"], extra: True}).status_code == 422


def test_unknown_ids_and_invalid_outcomes_rejected(client):
    assert client.post("/predict", json={"history": [], "candidate_ids": ["missing"]}).status_code == 404
    assert client.post("/attempts", json={"student_id": "demo", "problem_id": "missing", "correct": True}).status_code == 404
    for updates in [{"correct": "false"}, {"student_id": "real-user"}, {"code": "System.exit(0);"}]:
        body = {"student_id": "demo", "problem_id": "java-sum", "correct": True, **updates}
        assert client.post("/attempts", json=body).status_code == 422


def test_invalid_history_and_nested_target_fields_rejected(client):
    item = {"problem_id": "java-sum", "sequence_index": 0, "correct": True, "attempt_number": 1}
    for history in [[item, item], [{**item, "sequence_index": -1}], [{**item, "target_correct": True}], [{**item, "correct": 1}]]:
        assert client.post("/predict", json={"history": history, "candidate_ids": ["java-sum"]}).status_code == 422


def test_ranking_is_stable_and_new_evidence_updates_profile(client):
    first = client.get("/students/demo/recommendations").json()
    second = client.get("/students/demo/recommendations").json()
    assert first["recommendations"] == second["recommendations"]
    assert first["snapshot_id"] != second["snapshot_id"]
    rows = first["recommendations"]
    assert rows == sorted(rows, key=lambda row: (-row["score"], row["problem_id"]))
    assert all(0 <= row["predicted_correctness"] <= 1 and row["reasons"] for row in rows)
    client.post("/attempts", json={"student_id": "demo", "problem_id": "java-reverse", "correct": False})
    concepts = {row["concept_id"]: row for row in client.get("/students/demo/profile").json()["concepts"]}
    assert concepts["strings"]["supporting_attempts"] == 1
    assert concepts["strings"]["estimated_performance"] == pytest.approx(1 / 3)


def test_simultaneous_attempts_receive_unique_numbers(client):
    client.get("/students/demo/history")
    def record(_):
        return client.post("/attempts", json={"student_id": "demo", "problem_id": "java-total", "correct": True})
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(record, range(4)))
    assert all(response.status_code == 201 for response in responses)
    assert sorted(response.json()["attempt_number"] for response in responses) == [1, 2, 3, 4]
    assert sorted(response.json()["sequence_index"] for response in responses) == [4, 5, 6, 7]


@pytest.mark.parametrize("history", [[], [{"problem_id": "java-sum", "sequence_index": 0, "correct": True, "attempt_number": 2}]])
def test_no_first_attempt_history_is_explicit_neutral_prior(client, monkeypatch, history):
    monkeypatch.setattr("api.main.storage.history", lambda: history)
    profile = client.get("/students/demo/profile").json()
    assert profile["total_interactions"] == len(history)
    assert profile["first_attempts"] == 0
    assert profile["retries"] == len(history)
    assert all(row["evidence_status"] == "no-history" and row["supporting_problem_ids"] == [] and row["estimated_performance"] == 0.5 for row in profile["concepts"])


def test_concept_support_is_distinct_first_attempts_not_retries(client):
    before = client.get("/students/demo/profile").json()
    concepts = {row["concept_id"]: row for row in before["concepts"]}
    assert concepts["strings"]["evidence_status"] == "no-history"
    assert concepts["conditionals"]["evidence_status"] == "limited-history"
    client.post("/attempts", json={"student_id": "demo", "problem_id": "java-reverse", "correct": False})
    after = client.get("/students/demo/profile").json()
    strings = next(row for row in after["concepts"] if row["concept_id"] == "strings")
    assert strings["supporting_problem_ids"] == ["java-reverse"]
    assert strings["supporting_attempts"] == 1
    assert strings["evidence_status"] == "limited-history"
    assert after["first_attempts"] == before["first_attempts"] + 1
    assert after["retries"] == before["retries"]
    client.post("/attempts", json={"student_id": "demo", "problem_id": "java-count", "correct": True})
    conditionals = next(row for row in client.get("/students/demo/profile").json()["concepts"] if row["concept_id"] == "conditionals")
    assert conditionals["evidence_status"] == "observed-first-attempt"
    assert conditionals["supporting_problem_ids"] == ["java-even", "java-max", "java-count"]


def test_generated_snapshot_binds_exact_ranking_history_and_versions(client):
    from api.recommendation_records import get_snapshot
    initial_history = client.get("/students/demo/history").json()
    response = client.get("/students/demo/recommendations")
    assert response.status_code == 200
    body = response.json()
    saved = get_snapshot(body["snapshot_id"])
    assert saved.snapshot.history_sequence_index == body["history_sequence_index"] == 3
    assert saved.snapshot.model_id == "demo-history-v1"
    assert saved.snapshot.policy_version == body["policy_version"]
    assert saved.snapshot.dataset_version == "synthetic-v1"
    assert saved.snapshot.calibrated is False
    assert [row.model_dump() for row in saved.snapshot.candidates] == [
        {key: row[key] for key in ("problem_id", "predicted_correctness", "score")}
        for row in body["recommendations"]]
    client.post("/attempts", json={"student_id": "demo", "problem_id": "java-reverse", "correct": False})
    later = client.get("/students/demo/recommendations").json()
    assert later["history_sequence_index"] == 4
    assert get_snapshot(body["snapshot_id"]) == saved
    assert initial_history == client.get("/students/demo/history").json()[:-1]


def test_generation_reads_one_history_snapshot_and_handles_empty_history(client, monkeypatch):
    calls = []
    def observed():
        calls.append(True)
        return []
    monkeypatch.setattr("api.main.storage.history", observed)
    body = client.get("/students/demo/recommendations").json()
    assert len(calls) == 1 and body["history_sequence_index"] == -1
    assert all(row["predicted_correctness"] == .5 for row in body["recommendations"])


def test_snapshot_write_failure_does_not_return_unrecorded_generation(client, monkeypatch):
    import sqlite3
    def fail(_):
        raise sqlite3.OperationalError("synthetic write failure")
    monkeypatch.setattr("api.main.record_snapshot", fail)
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.get("/students/demo/recommendations")
    assert response.status_code == 500
    assert "snapshot_id" not in response.text
    assert "synthetic write failure" not in response.text
