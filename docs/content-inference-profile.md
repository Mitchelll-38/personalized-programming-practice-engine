# Offline content inference profile

Owner: model platform engineer. Dependencies: content checkpoint #55, offline cache
reader #58 and label-free adapter #66. Purpose: measure repeated loaded-adapter
software cost for trusted synthetic queries without encoder/network or evaluation.
Acceptance: bounded strict label-free queries/config, exact checkpoint/query/cache
identities, separate checkpoint/query/cache-load phases and warmup/repeat counts,
aggregate timings only, and restored caller CPU RNG/thread/determinism/device state.

Plan recorded before implementation: read one trusted synthetic checkpoint and
bounded query JSON; load exact permitted frozen entries offline from its declared
encoder; hash the inventory/config; warm up and repeatedly call the reviewed
adapter under a scoped one-thread deterministic CPU policy. Report nearest-rank
latencies/throughput with clear scope (feature building and integrity included;
encoder/network excluded). Test clocks/call counts, gates/hashes/corruption,
settings restoration and CLI. No fit, test partition, prediction metrics, model
selection, API activation or published performance-benefit claim is added.

`profile_content_inference(model_directory, query_file, encoder_directory,
repeats=20, warmups=2, batch_size=32)` loads a trusted declared-synthetic checkpoint.
Query JSON is `{"inputs": [<PredictionInput>, ...]}` with no target labels/code:
1–256 queries, at most 256 historical interactions each, at most 8 MiB and no
duplicate object fields. Repeats are 1–100, warmups 0–10 and adapter mini-batches
1–256. Invalid bounds fail before files are opened. Canonical causal validation
precedes offline entry access; unverified checkpoints and missing/changed entries
fail. No encoder is initialized, input is sent remotely, model is fitted or labels
are evaluated. The caller supplies immutable private trusted inputs/permissions.

The JSON receipt binds declared metadata/weights hashes, exact query bytes,
encoder config/hash and sorted key→entry-checksum inventory hash/count/namespace,
architecture and Python/Torch/system identity. It includes no query values,
learner/problem IDs, input paths or row predictions. Hashes establish declared
integrity, not authenticated origin. Keep redirected receipts in ignored storage.

Checkpoint loading, query parsing, cache loading and total warmup milliseconds are
separate from sampled inference. Each measured sample scores the entire query
inventory (internally mini-batched); batch min/median/nearest-rank p95/max and
throughput cover the loaded adapter, including causal validation, frozen-vector
feature construction and live checkpoint/cache integrity. File loading, optional
library import startup, warmups and encoder/network work are excluded from those
samples. The encoder/network are never used by this workflow. Zero clock duration
produces null throughput rather than division by zero.

One deterministic CPU thread is scoped to the complete profile, preserving caller
CPU RNG/thread/determinism/warn-only and ambient default-device state on success or
failure. Concurrent global Torch setting changes/profiles in one process are
unsupported. Local timings depend on hardware, workload and environment: they
are software execution observations, not predictive-quality, learning-benefit,
capacity, hosted-service latency or model-improvement evidence.

```powershell
.\.venv\Scripts\python.exe -m practice_engine.content_inference_profile `
  .data/private/data/content-runs/synthetic-smoke/model `
  .data/private/data/content-queries.json `
  --encoder-directory .data/private/data/encoders --repeats 20 --warmups 2
```

Install the optional neural environment and prepare the exact cache separately.
There is no download, training, test-evaluation or API-activation option here.
