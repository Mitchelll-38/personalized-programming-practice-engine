# DKT checkpoint boundary

Owner: engineer C. Purpose: persist and reload a DKT model independently of the later trainer. Dependencies: the causal DKT forward module and optional CPU Torch environment. Acceptance: known-exercise reload parity; strict, hashed configuration/vocabulary/state; no-clobber atomic directory publication; and a validated training-population fallback for unknown candidates. No training or API activation is included.

`save_dkt_checkpoint(directory, model, vocabulary, provenance, training_total=..., training_correct=...)` writes `weights.pt` and `metadata.json`. The destination must not exist. Detached CPU float32 state copies are validated before serialization. A sibling staging directory and cooperating-writer lock publish both files together by same-filesystem rename; failures clean staging and release the lock. Abrupt process termination can leave a staging directory or lock requiring manual cleanup; it never exposes a partially written destination.

`load_dkt_checkpoint(directory)` verifies the metadata checksum and weights SHA-256, reconstructs only the fixed single-layer DKT configuration, and loads a tensor state dictionary with `torch.load(weights_only=True, map_location="cpu")`. Keys, shapes, float32 dtypes and finite values must match exactly. The loader checks those fields and adequate tensor storage before constructing the model, then retains the reconstructed-state validation. These checks detect corruption and restrict deserialization; hashes do not authenticate the author or prove training provenance. Only load artifacts from a trusted research workflow.

The returned artifact's `predict(examples)` preserves causal-history validation and outputs uncalibrated correctness probabilities. Known candidate IDs use the saved neural head. **Unknown candidate IDs always use `(training_correct + 1) / (training_total + 2)`**, the fixed Beta(1,1) smoothed training-population rate, because the UNK head has no training targets. Strict integer counts must satisfy `training_total > 0` and `0 <= training_correct <= training_total`. Supplying the correct training-partition counts is the caller's responsibility; no labels are fitted or inspected by the checkpoint writer. Unknown historical IDs still map to UNK in recurrence.

Loaded inference also checks a deterministic tensor-content fingerprint before each prediction and rejects live weight mutations. This scans all parameter bytes, so each call has linear checkpoint-size overhead; batch calls amortize that cost. Only a checksum is retained, using transient views of contiguous CPU tensors rather than storing a second binary checkpoint. Metadata mutations are revalidated as well. The returned artifact is an inference boundary, not an editable training model.

Metadata records train-only provenance, vocabulary, all model dimensions, versions, fallback counts and `calibrated=false`. The artifact retains synthetic/unverified declarations; creating or saving random weights is not evidence of a trained model or research quality. This module imports Torch only when explicitly used; generic baseline serving remains unchanged. Keep checkpoints in ignored `artifacts/`, never public git.

## October 19 checkpoint context isolation

Owner: model engineer. Purpose: keep checkpoint save/load from changing the
caller's CPU initialization RNG and restore CPU checkpoints independently of the
caller's default device. Reproduction before implementation: `_restore` advanced
CPU RNG and failed with `Cannot copy out of meta tensor` under a meta-device
context; content checkpoint reconstruction already scopes both boundaries.
Acceptance: public save/load leave CPU RNG unchanged on success and validation
failure, load on CPU under an alternate default device, preserve caller context,
and retain prediction parity/unknown fallback. Dependencies: existing Torch DKT
checkpoint contract and original synthetic fixtures. No trainer, architecture,
provenance, data import or empirical run behavior changes are included.
Plan recorded before code: scope only fresh model construction to CPU and a
CPU-only RNG fork, then reuse the existing tensor-state validation/loading path.

## October 27 live architecture integrity

Owner: model engineer. Purpose: reject DKT module changes that alter inference
without changing the saved tensor bytes. A loaded embedding's `max_norm` can be
changed after loading; the current pre-inference tensor fingerprint then passes,
while the next embedding call renormalizes weights and returns an altered score.
The checkpoint writer likewise must not serialize a model whose live module
behavior differs from the fixed architecture reconstructed by the reader.

Acceptance: saving a model with changed embedding or LSTM/head semantics fails
before publication; a loaded checkpoint rejects a live semantic change on the
first prediction; unchanged checkpoints retain known/unknown prediction parity.
Keep architecture checks distinct from tensor-content fingerprinting. Dependencies:
the existing DKT forward/checkpoint contracts and synthetic fixture only. This
fix does not change training, input causality, provenance or empirical results.

Independent review found that registered forward hooks also change live behavior
without changing tensor bytes and disappear on reload. The acceptance boundary
therefore includes module-local and process-wide forward/pre-forward hooks: reject
them before saving and before the first loaded prediction, while preserving the
ordinary hook-free round trip. Backward hooks do not run during inference.

## Validate state dimensions before reconstruction

Owner: model platform engineer. Purpose: reject a hash-valid checkpoint whose
declared dimensions disagree with its saved tensors before allocating a model.
Acceptance: oversized or otherwise mismatched metadata/state keys, shapes and
dtypes fail before DKT construction; a valid checkpoint still reloads with exact
known/unknown prediction parity. Dependencies: the fixed DKT state layout and
existing metadata/weights hash checks. The guard does not limit a genuinely large
matching checkpoint or make arbitrary hostile storage safe to load.
