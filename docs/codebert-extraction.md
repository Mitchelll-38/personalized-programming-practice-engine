# Frozen local CodeBERT extraction

Owner: model platform engineer. Purpose: extract fixed local vectors from permitted
query content and reuse the reviewed private cache. Dependencies: cache PR #35 and
optional encoder environment PR #39. Acceptance: pinned verified assets, explicit
contained Hub/Xet caches, default offline loading, frozen CPU inference, declared
mask-aware pooling, causal label-free content selection and finite cached output.

Plan: validate the fixed official snapshot and storage environment; load only local
RoBERTa/tokenizer code with weights-only deserialization; encode candidate/history
statements and strictly previous historical code; publish/reuse exact-content cache
entries. Mocked tests cover download flags, environment containment, pooling,
causality, invalidation and corruption. Any real-weight smoke is a separate private
receipt using original synthetic text, never real student submissions.

No model training, content LSTM, calibrated predictions or API activation is part
of this change. The coordinator owns chronological progress records.

## Explicit inference policy

Only `microsoft/codebert-base` revision
`3b0952feddeffad0063f274080e3c23d75e7eb39`, its matching tokenizer and 768 dimensions
are supported. Configuration caps the total tokens at 2–512, including special
tokens. Tokenization uses fast RoBERTa, adds special tokens, right-pads batches and
uses the configured left/right truncation. Mean pooling includes **all nonpadding
tokens, including beginning/end special tokens**; `cls` selects the first token.
CPU float32 inference uses evaluation mode and disables gradients. It never
fine-tunes the encoder. Do not mutate the private backend after construction.

Set `HF_HOME` and `HF_XET_CACHE` before optional Hub/Transformers imports. The
adapter rejects missing/mismatched paths, including constants already initialized
under a different home; use a fresh configured process. It changes no environment
variables or authentication settings and requests no saved token. Asset reads use
an explicit private cache and pinned revision; the five config/tokenizer Git blob
IDs and PyTorch weight SHA-256 are checked before model loading. Remote code is
disabled, and unexpected snapshot files are rejected so an unverified
`tokenizer.json`/`added_tokens.json` cannot override the checked vocabulary. The
official binary loads with `weights_only=True` on the pinned
CPU Torch backend. The source/license observations and remote file digest are
documented in [encoder-environment.md](encoder-environment.md).

By default assets must already exist locally. `allow_download=True` permits public
asset downloads only; it does not override an operator-set `HF_HUB_OFFLINE=1`.
After initialization, encoding receives only a validated `PredictionInput`.
Historical statements/code are emitted in history order, followed by the candidate
statement. Missing/blank historical code is omitted; no target label or candidate
code is accepted. Equal role/content requests reuse one entry while output order
and repeated occurrences are preserved.

Cache files live under `embeddings/frozen-codebert-v1/` inside the private encoder
directory, so earlier caller-provided fixture files in a generic cache location
are not accidentally accepted as encoder output. Each entry retains the reviewed
exact-content/config integrity format. This namespace defines the float32, fast
tokenizer and pooling policy above; change it when those semantics change.
Checksums are not producer authentication. Use a trusted private cache; arbitrary
vectors can be written with recomputed hashes. Corrupt entries fail rather than
being silently replaced. Publication is atomic per entry; failed batches may leave
earlier valid entries. Model/batch memory remains a local CPU resource cost.

Example from the main project root, in a fresh process:

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.data/private/data/encoders/huggingface'
$env:HF_XET_CACHE = Join-Path $env:HF_HOME 'xet'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
# Keep HF_HUB_OFFLINE=1 for local-only use; clear it explicitly before an authorized download.
```

Pass `.data/private/data/encoders/` as the adapter directory. The caller manages
the label-free query and optional download flag; imports and ordinary tests never
fetch weights. Actual encoder smoke receipts must distinguish real pretrained
execution on original synthetic strings from predictive or learning results.
