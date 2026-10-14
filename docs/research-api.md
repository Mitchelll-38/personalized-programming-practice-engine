# Opt-in synthetic baseline API

Owner: baseline engineer. Purpose: expose reviewed JSON baselines without changing
the replay demo. Acceptance: label-free bounded prediction requests, synthetic-only
artifact serving, fail-closed private errors and unchanged demo behavior.
Dependencies: baseline artifacts, training commands and the label-free serving
boundary (PRs #21, #29, #30). DKT, calibration and UI selection remain separate work.

Set a trusted **server-side** path to a synthetic rate/logistic/BKT `model.json`:

```powershell
$env:PRACTICE_RESEARCH_MODEL = 'C:\private\runs\logistic-smoke\model.json'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

`GET /research/model` reports model/feature/artifact versions, payload hash,
dataset/source kind and declared source/split provenance. It explicitly identifies
synthetic, uncalibrated software-test output (`research_results=false`). This
declaration does not authenticate data permission or empirical predictive quality.

`POST /research/predict` takes an object with only `inputs`: 1–1000 label-free
queries. Each query has `student_id`, `target_sequence_index`, `history` and
`candidate` as defined in [prediction-serving.md](prediction-serving.md).
Histories are limited to 10000 interactions per query. Candidate statements and
concepts are supplied explicitly; IDs need not belong to the demo catalog.
Strict causal first-attempt checks reject future, wrong-student, retry and candidate
responses. Target outcomes/code and unknown request fields are forbidden (422).
Responses preserve query order and return `model` metadata plus finite
`predictions` containing problem ID and p(correct). These routes store no attempts.

Absent configuration returns 503 `research_model_not_configured`. Missing,
malformed, tampered, unsupported or unverified-source artifacts return 503
`research_model_unavailable`, without paths, payloads or loader exception details.
The server loads and validates the artifact once per request, so replacements are
observed immediately and no stale cache exists. This is a local prototype: use
atomic artifact replacement; large artifacts/batches incur loading/inference cost.
Never configure an untrusted file or expose this unauthenticated demo publicly.

`/models/current`, `/predict`, learner profiles, recommendations and the dashboard
continue using the existing synthetic heuristic. Configuring the research path
does not select it for replay, train a model or establish learning effectiveness.
