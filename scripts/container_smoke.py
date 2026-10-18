"""Real HTTP checks against an isolated synthetic container instance."""

import argparse
import json
from pathlib import Path
import urllib.error
import urllib.request


def request(base, path, payload=None, *, status=200, raw=False):
    data = None if payload is None else json.dumps(payload).encode()
    call = urllib.request.Request(base + path, data, {"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(call, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        content = response.read()
        if response.status != status:
            raise AssertionError(f"{path}: expected HTTP {status}, got {response.status}")
    return content.decode() if raw else json.loads(content)


def replay(base, state):
    assert 'id="root"' in request(base, "/", raw=True)
    assert request(base, "/api/health") == {"status": "ok"}
    assert "url: '/api/openapi.json'" in request(base, "/api/docs", raw=True)
    schema = request(base, "/api/openapi.json")
    assert "/attempts" in schema["paths"] and {"url": "/api"} in schema["servers"]
    before = request(base, "/api/students/demo/history")
    ranking = request(base, "/api/students/demo/recommendations")
    assert ranking["is_demo"] is True and ranking["policy_version"] == "transparent-ranking-v2"
    problem = ranking["recommendations"][0]["problem_id"]
    choice = request(base, "/api/recommendation-choices", {
        "snapshot_id": ranking["snapshot_id"], "problem_id": problem}, status=201)
    assert request(base, "/api/students/demo/history") == before
    payload = {"student_id": "demo", "problem_id": problem, "correct": True,
               "choice_id": choice["choice_id"]}
    outcome = request(base, "/api/attempts", payload, status=201)
    assert request(base, "/api/attempts", payload, status=201) == outcome
    assert outcome["problem_id"] == problem and outcome["correct"] is True
    after = request(base, "/api/students/demo/history")
    assert len(after) == len(before) + 1 and after[-1] == outcome
    request(base, "/api/attempts", {**payload, "correct": False}, status=409)
    assert request(base, "/api/students/demo/history") == after
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"history": after, "payload": payload, "outcome": outcome}), encoding="utf-8")
    print("Container proxy, schema, choice, linked retry and conflict checks passed")


def verify(base, state):
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert request(base, "/api/students/demo/history") == saved["history"]
    assert request(base, "/api/attempts", saved["payload"], status=201) == saved["outcome"]
    assert request(base, "/api/students/demo/history") == saved["history"]
    print("Restart retained history and linked idempotency receipt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("replay", "verify"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--state", type=Path, required=True,
                        help="Private synthetic receipt path; use ignored project storage")
    values = parser.parse_args()
    {"replay": replay, "verify": verify}[values.phase](values.base_url.rstrip("/"), values.state)


if __name__ == "__main__":
    main()
