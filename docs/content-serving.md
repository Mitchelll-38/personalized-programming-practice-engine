# Label-free cached-content checkpoint adapter

Owner: model platform engineer. Dependencies: validated content batches #49,
content forward #53/checkpoint #55 and label-free serving inputs. Purpose: score
causal candidate queries using an already-loaded checkpoint and supplied exact
cached entries, without artifact/file/network activation. Acceptance: strict
label-free revalidation, checkpoint-derived encoder/vocabulary, finite ordered
scores, cold/unknown content, bounded mini-batches, live integrity even for empty
queries, and no encoder/API activation.

Plan before implementation: expose predict_content_inputs(checkpoint, queries,
entries, batch_size=32), validate its typed boundary and causal queries, derive
features from checkpoint metadata through the reviewed batch producer, invoke
checkpoint inference and wrap finite sigmoid scores. Factor a public integrity
check from checkpoint.logits for empty-batch coverage. Test direct-forward parity,
order, unknown/cold/causal/cache tampering, invalid inputs and live mutations.

`predict_content_inputs(checkpoint, queries, entries, batch_size=32)` accepts an
already-loaded strict `ContentCheckpoint`, a list/tuple of label-free
`PredictionInput` objects and a supplied cache-entry mapping. It accepts no file
paths, encoder overrides, target outcomes or submitted target code. The encoder
and training-only concept vocabulary come exclusively from checkpoint metadata.
Every query is detached and revalidated before constructing canonical batches;
the legacy example producer receives only a fixed internal False sentinel, which
is absent from forward tensors. Outputs preserve query order and candidate IDs
as finite `PredictionScore` probabilities from sigmoid logits.

Candidate IDs have no learned identity embeddings; unseen exercises retain exact
candidate content. Unknown concepts contribute zero, and cold history uses the
model's zero state. Missing/wrong-role/wrong-encoder/corrupt used entries fail through
the strict producer. Unused entries may remain in a larger supplied map. Live
metadata/weights/architecture integrity and registered forward/pre-hook absence
are checked even when queries are empty.
Only required entries are consumed; no encoder is constructed or data fetched.

Mini-batches are bounded to 1–256. History/query inventory size remains a trusted
caller resource decision. Feature allocation is explicitly CPU and preserves the
caller's ambient device. The adapter does not change process-global thread/RNG
or deterministic settings; callers needing bitwise comparison with a training run
must use its one-thread deterministic CPU policy. Small floating-point changes
across batch shapes/thread counts are possible. The default API does not import
this optional Torch module and no registry or research route activates it.

The caller owns provenance and permission gates and must supply trusted loaded
artifacts/entries; checksums are content integrity rather than origin proof. Scores
are uncalibrated and inherit the checkpoint's documented training status. Synthetic
software checks establish no predictive quality, proven mastery or learning benefit.

## Content checkpoint forward-hook integrity repair

Owner: model platform engineer. Purpose: reject registered PyTorch forward and
forward-pre hooks that can change content checkpoint predictions without changing
metadata or tensor checksums. Acceptance: saving a hooked content model fails
before publication; a hooked loaded checkpoint fails integrity checks and serving;
unmodified models still save, reload and predict. Dependencies: existing strict
content checkpoint format and label-free content serving adapter. This repair does
not change checkpoint files, model architecture or inference inputs.
