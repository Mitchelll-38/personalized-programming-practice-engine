# Preparing content features for synthetic training runs

Owner: coordinator. Purpose: prepare frozen content cache entries from a verified
synthetic train/validation bundle, then let a separate trainer load them offline.
Dependencies: shared bundle verifier, frozen CodeBERT #45 and content inputs #49.
Acceptance: source/integrity gates before encoding; causal label-free queries only;
no test example parsing; exact cache identities/integrity; private cache writes;
aggregate inventory receipt without text, labels or learner/problem identifiers.

Plan: verify the bundle, initialize the explicit private frozen encoder and encode
training/validation query content only. Reopen required entries through the same
strict loader intended for training and record deterministic content-entry hashes,
encoder and bundle provenance. A separate load_content_entries helper revalidates
examples and reads matching entries without network. No model fitting, checkpoint
publication, API activation or empirical quality result is part of this change.


`prepare_content_cache(bundle, directory, config=..., allow_download=False)` uses
only the shared loader's verified train/validation examples. Test bytes are hashed
for bundle integrity but never decoded or converted to feature queries. Every
encoder request is a revalidated label-free `PredictionInput`. Reopening the cache
checks exact content, role/config and entry integrity. The returned receipt binds
manifest/provenance, encoder policy/namespace, counts and sorted unique content
entry hashes; it contains no text, code, labels or learner/problem identifiers.
It is a declared software receipt, not authenticated encoder/data permissions.

`load_content_entries(examples, directory, config)` reads those required private
entries offline without initializing optional model libraries. The trainer owns
partition membership, uses a verified bundle and supplies the checkpoint's exact
encoder configuration. Missing, corrupt or mismatched entries fail. Preparation
performs no fitting. Existing valid cache entries can survive an interrupted or
failed preparation; a changed manifest prevents returning a completed receipt.

Run from the main root after installing the optional encoder environment and
setting its private HF_HOME/HF_XET_CACHE as described in [codebert-extraction.md](codebert-extraction.md):

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.content_cache `
  artifacts/inference-profile-smoke/bundle `
  --encoder-directory .data/private/data/encoders --max-tokens 32
```

The default is local-only, with explicit optional `--allow-download` for the fixed
public model assets; no content is sent to remote inference. `--pooling` and
`--truncation` form part of the cache identity. Stdout is JSON; keep any redirected
receipt under ignored project storage. The source gate currently admits synthetic
bundles only. Tests use original synthetic vectors and mocked backends; actual
pretrained extraction is recorded separately, not inferred from mocks.
