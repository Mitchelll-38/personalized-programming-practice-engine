import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from api.catalog import BY_ID
from api.heuristics import recommend
from api.main import app
from api.practice_policy import PracticePolicy
from api.recommendation_records import RecommendationSnapshot, ScoredCandidate, get_snapshot, list_snapshots, record_snapshot
from practice_engine.models.artifacts import payload_hash


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "demo.sqlite3"
    monkeypatch.setenv("PRACTICE_DB_PATH", str(path))
    monkeypatch.delenv("PRACTICE_POLICY_CONFIG", raising=False)
    with TestClient(app) as api:
        yield api, path


@pytest.mark.parametrize("change", [{"challenge_lower": .8, "challenge_upper": .6},
    {"challenge_lower": .6, "challenge_upper": .6}, {"challenge_upper": 1.1},
    {"challenge_lower": True}, {"need_weight": float("nan")}, {"repeat_penalty": -1.},
    {"prerequisite_threshold": float("inf")}, {"policy_version": "unknown"}, {"unknown": .1}])
def test_bad_policy_values_rejected(change):
    with pytest.raises(ValueError):
        PracticePolicy(**change)


def test_distance_outside_range_and_stable_ties_are_transparent(monkeypatch):
    ids = list(BY_ID)[:3]
    monkeypatch.setattr("api.heuristics.estimate", lambda *_: [
        {"problem_id": key, "predicted_correctness": probability}
        for key, probability in zip(ids, (.4, .7, .9))])
    rows = recommend([], PracticePolicy(need_weight=0., prerequisite_penalty=0., repeat_penalty=0.))
    assert {row["problem_id"]: row["score"] for row in rows} == dict(zip(ids, (.8, 1., .9)))
    monkeypatch.setattr("api.heuristics.estimate", lambda *_: [
        {"problem_id": key, "predicted_correctness": .7} for key in reversed(ids)])
    assert [row["problem_id"] for row in recommend([], PracticePolicy(need_weight=0., prerequisite_penalty=0., repeat_penalty=0.))] == sorted(ids)


def test_observed_need_and_repetition_use_first_attempt_support():
    policy = PracticePolicy(challenge_lower=.4, challenge_upper=.8, prerequisite_threshold=0.)
    first = {"problem_id": "java-sum", "sequence_index": 0, "attempt_number": 1, "correct": True}
    rows = recommend([first], policy)
    assert next(row for row in rows if row["problem_id"] == "java-sum")["score"] == .733333
    assert recommend([first, {**first, "sequence_index": 1, "attempt_number": 2, "correct": False}], policy) == rows
    with pytest.raises(ValueError):
        recommend([], policy.model_copy(update={"challenge_upper": -1.}))


def test_response_and_snapshot_bind_exact_loaded_policy_once(client, tmp_path, monkeypatch):
    api, _ = client
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"challenge_lower": .3, "challenge_upper": .5, "need_weight": .4}))
    monkeypatch.setenv("PRACTICE_POLICY_CONFIG", str(path))
    body = api.get("/students/demo/recommendations").json()
    config = PracticePolicy(challenge_lower=.3, challenge_upper=.5, need_weight=.4)
    assert body["policy_version"] == config.policy_version
    assert body["policy_config"] == config.model_dump()
    assert body["policy_sha256"] == payload_hash(config.model_dump())
    saved = get_snapshot(body["snapshot_id"])
    assert saved.snapshot.policy_config == config and saved.snapshot.policy_sha256 == body["policy_sha256"]
    assert any("30.0%-50.0%" in reason for row in body["recommendations"] for reason in row["reasons"])
    path.write_text(json.dumps({"challenge_lower": .7, "challenge_upper": .9}))
    later = api.get("/students/demo/recommendations").json()
    assert later["policy_sha256"] != body["policy_sha256"]
    assert get_snapshot(body["snapshot_id"]) == saved
    calls = []
    def loaded():
        calls.append(True)
        return config
    monkeypatch.setattr("api.main.configured_policy", loaded)
    assert api.get("/students/demo/recommendations").status_code == 200
    assert len(calls) == 1


@pytest.mark.parametrize("payload", ['{"challenge_lower":true}', '{"challenge_lower":0.6,"challenge_lower":0.7}',
    '{"private-path":"not exposed"}', 'invalid JSON', '[]'])
def test_bad_server_config_fails_without_recording_or_disclosing_path(client, tmp_path, monkeypatch, payload):
    api, _ = client
    path = tmp_path / "private-policy.json"
    path.write_text(payload)
    monkeypatch.setenv("PRACTICE_POLICY_CONFIG", str(path))
    response = api.get("/students/demo/recommendations")
    assert response.status_code == 503 and response.json() == {"detail": "practice_policy_unavailable"}
    assert str(path) not in response.text and "not exposed" not in response.text
    assert list_snapshots() == []
    assert api.get("/students/demo/profile").status_code == 200


def test_snapshot_policy_binding_revalidates_copies_and_old_records_remain_readable(client):
    api, path = client
    body = api.get("/students/demo/recommendations").json()
    saved = get_snapshot(body["snapshot_id"])
    for change in ({"policy_sha256": "0" * 64}, {"policy_version": "different"}, {"policy_sha256": None},
                   {"policy_config": None, "policy_sha256": None}):
        with pytest.raises(ValueError):
            record_snapshot(saved.snapshot.model_copy(update=change))
    assert len(list_snapshots()) == 1
    old = record_snapshot(RecommendationSnapshot(model_id="demo-history-v1", policy_version="demo-ranking-v1",
        dataset_version="synthetic-v1", history_sequence_index=-1,
        candidates=(ScoredCandidate(problem_id="java-sum", predicted_correctness=.5, score=.7),)))
    legacy = json.loads(old.model_dump_json())
    legacy["snapshot"].pop("policy_config")
    legacy["snapshot"].pop("policy_sha256")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE recommendation_snapshots SET payload_json=? WHERE snapshot_id=?",
                   (json.dumps(legacy), old.snapshot_id))
    assert get_snapshot(old.snapshot_id) == old

    stripped = json.loads(saved.model_dump_json())
    stripped["snapshot"].pop("policy_config")
    stripped["snapshot"].pop("policy_sha256")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE recommendation_snapshots SET payload_json=? WHERE snapshot_id=?",
                   (json.dumps(stripped), saved.snapshot_id))
    with pytest.raises(ValueError, match="Version 2"):
        get_snapshot(saved.snapshot_id)
    assert get_snapshot(old.snapshot_id) == old
