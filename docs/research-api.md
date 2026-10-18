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
synthetic software-test output and calibration status (`research_results=false`). This
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

## Calibrated baseline envelopes

The same server path can select `temperature-baseline-artifact-v1` envelopes from
the [validation calibration workflow](calibration-runs.md). No separate endpoint
or configuration knob is added. The underlying base must still declare synthetic
source data. Loading validates the embedded base, envelope/fitting hashes and
matching provenance; unknown versions and modified artifacts fail closed with the
same private 503 response. Files are read once per request and parsed in memory.

Calibrated metadata keeps the underlying model/feature/payload identity, sets
`artifact_version` to the envelope version and `calibrated=true`, and adds
`base_artifact_version`, `base_artifact_sha256`, `artifact_sha256` plus `calibration`.
The latter declares the temperature-scaling method, scalar and full validation
fitting record: partition, source/split provenance, validation/probability hashes,
fitting count and predeclared grid. `is_synthetic=true` and `research_results=false`
remain explicit. Hashes and records are declarations, not authenticated provenance.
`calibrated=true` means a fitted scalar is applied; it does not certify empirical
calibration quality, especially on the same validation observations used to fit it.

Label-free queries and existing limits are unchanged. The adapter preserves live
envelope integrity checks and applies the scalar to base probabilities. Existing
uncalibrated baseline responses are unchanged. The current inspector deliberately
rejects calibrated responses rather than labeling them uncalibrated; presenting
calibration in the UI is a separate change. Replay continues using the heuristic.
