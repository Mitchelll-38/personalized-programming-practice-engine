# Verified synthetic content training runs

Owner: model platform engineer. Dependencies: offline content-cache PR #58,
optimizer core PR #59, content checkpoint #55 and shared bundle verification.
Purpose: verify synthetic train/validation provenance and exact offline cached
features, fit/select the content model, prove checkpoint reload parity, and publish
one complete private run. Acceptance: test bytes hashed but examples never decoded;
no encoder/download; inventory/config hashes; aggregate validation and epoch
metadata; atomic new-directory publication, no-clobber and cleanup on failure.

Plan recorded before implementation: load a verified synthetic bundle with stable
manifest bytes, load only train/validation cache entries through the shared offline
helper, hash their exact inventory and encoder/config, call the separate optimizer,
save/reload the selected checkpoint and reproduce ordered validation probabilities.
Publish model/validation/run metadata together under an owned cooperating-writer
lock. CLI selects bounded optimizer and frozen encoder policy; no dataset import,
cache extraction, calibration, serving activation or real-data result is bundled.

`train_content(bundle, directory, output, encoder=..., config=...)` verifies the
shared synthetic bundle before cache loading. The offline cache reader revalidates
only permitted train/validation content with exact role/config/entry integrity;
missing or changed entries fail without fetching anything. Test bytes remain part
of bundle integrity hashing and are never parsed or encoded. Manifest bytes must
remain stable through verification and publication. Concurrent changes to bundle
files or cache/model objects are unsupported; use immutable private inputs.

The complete new run contains `model/metadata.json`, `model/weights.pt`,
`validation.json` and `run.json`. The run records bounded config/seed and hash,
exact encoder and hash, namespace and unique entry-inventory hash/count, source and
split provenance, processing-manifest hash, aggregate epoch losses/selection,
validation-only metrics, checkpoint hashes and exact reload parity. The inventory
hash binds the sorted key→entry-checksum map plus encoder and namespace. It is a
declared content identity, not encoder-origin or permission authentication.
No per-row predictions, learner/problem IDs, text/code, labels or cache vectors
are persisted. Vocabulary tags and learned weights follow the checkpoint contract.
Validation fields are explicitly limited to `aggregate`, `equal_student_macro`
and `metric_definitions`; future evaluator output fields are not published.
Checkpoint replay uses one deterministic CPU thread, matching optimizer validation,
and restores caller threads/determinism/warn-only settings even on replay failure.

Publication uses same-filesystem staging and an owned cooperating-writer lock.
Existing destinations/competing locks are preserved and owned temporary state is
cleaned on validation, checkpoint or parity failures. Uncooperative filesystem
writers and power-loss durability remain outside this local contract. Keep all
runs under ignored project storage. Defaults are 30 epochs with patience 5;
all optimizer options come from [content-training.md](content-training.md).

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.content_run `
  artifacts/inference-profile-smoke/bundle `
  --encoder-directory .data/private/data/encoders `
  --output .data/private/data/content-runs/synthetic-smoke `
  --max-tokens 32 --max-epochs 3 --patience 2
```

Prepare the exact matching private cache first using
[content-cache-preparation.md](content-cache-preparation.md). `--pooling` and
`--truncation` are part of the identity. There is no download flag here. Stdout is
the aggregate run JSON. Synthetic fitted predictions remain uncalibrated software
smoke results; real-data research, predictive benefit and learning effectiveness
remain unestablished. The API/registry is unchanged.
