# Offline inference timing

Owner: coordinator. Purpose: measure repeatable local batch inference cost with
artifact/query identities, separately from predictive quality. Dependencies:
portable/calibrated artifact loaders and label-free serving. Acceptance: known
synthetic artifacts only; strict causal label-free query array; bounded warmups
and timed repeats; exact read identities; aggregate timing/environment metadata;
no fitting, test evaluation, encoder extraction, API activation or per-row output.

Plan: read and validate one artifact and query file, warm the already-loaded model,
then time full label-free adapter calls including query/live-integrity validation.
Report batch median/p95/min/max and throughput with repeat/warmup/batch sizes and
hashes. Model loading is reported separately. These are repeated calls on one fixed
batch, not independent production request latency samples. Network/UI/SQLite and
CodeBERT extraction are excluded. Timing cannot establish model quality or learning
effectiveness. Original synthetic input fixtures only while real-data gates remain.


Run from the project root after creating a trusted synthetic baseline artifact and
an original synthetic query JSON object `{ "inputs": [...] }` using the same
label-free input shape as the research API:

```powershell
.\.venv\Scripts\python.exe -m practice_engine.inference_profile `
  artifacts/runs/baseline/model.json artifacts/queries/synthetic.json `
  --repeats 20 --warmups 2
```

The command prints JSON without per-row inputs/predictions or file paths. Redirect
to an ignored local artifact file if needed. `artifact_sha256` and `queries_sha256`
bind the exact bytes read; synthetic source is the model's declared provenance,
not an independent verification of query origin. The operator supplies permitted
original synthetic queries. Corrupt/unknown/unverified artifacts and target fields
fail before timed predictions. One to 1000 queries, up to 10000 earlier responses
per query, 1-1000 repeats and 0-100 warmups are accepted. No test partition is read.

`artifact_load_ms` measures read/parse/validation before queries and warmup; it is
not a guaranteed cold disk measurement. Batch timings use a monotonic nanosecond
clock and nearest-rank p95; throughput aggregates the measured adapter calls.
Zero total clock ticks yield null throughput. A short repeated sample is useful
for local software comparison, not a production latency guarantee. Record machine
hardware/load separately when comparing runs; Python/system/architecture alone
do not fully describe hardware. Neural checkpoints/encoder timing are separate.
