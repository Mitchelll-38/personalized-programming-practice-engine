# Content LSTM checkpoint contract

Owner: model platform engineer. Dependency: content forward PR #53. Purpose: persist
one causal forward model with its exact architecture, training-fitted concept
vocabulary, declared frozen encoder and fixed feature semantics, without rows or
embedding caches. Acceptance: CPU float32 finite exact state; strict portable JSON
and checksums; reload parity; metadata/config/vocabulary/encoder corruption and
live mutation detection; no-clobber publication and cleanup. The coordinator owns
chronological records. No trainer, serving activation or empirical results are added.

Plan recorded before implementation: bounded architecture metadata validates before
allocation and enforces encoder/model dimensions and vocabulary size. A fresh
canonical model validates exact state keys/shapes/dtypes. Publish only a new
checkpoint directory using a cooperating-writer lock and staged rename. Load strict
JSON and hashed bytes with CPU `weights_only=True`; revalidate metadata and live
state before returning logits. Test parity, boundaries, corruption, conflicting
publishers and injected failures. No generic serialization framework is introduced.

`save_content_checkpoint(directory, model, vocabulary, encoder, provenance)`
creates exactly `metadata.json` and `weights.pt`. It accepts canonical ContentLSTM
modules with actual CPU float32 finite tensors; it does not silently cast or move
the supplied model. Vocabulary/provenance must be training-only. Metadata binds
the exact encoder repository/revisions/tokenizer/pooling/truncation/token limit,
input dimension, concept vocabulary, architecture and fixed feature version.
Dimensions are bounded before restore allocation: vocabulary 10,000; input 4,096;
projection 256; concept 128; correctness 32; hidden 256. These limits keep this CPU
prototype bounded rather than supporting arbitrary checkpoint architectures.

`load_content_checkpoint(directory)` rejects duplicate JSON fields, unsupported
versions, extra metadata, invalid identities/checksums and state keys/shapes/types
or nonfinite weights. Deserialization uses `weights_only=True`, `map_location=cpu`;
the new canonical model is in evaluation mode and does not advance initialization
RNG. `checkpoint.logits(ContentInputs)` checks live metadata, architecture and weight
integrity, then returns finite uncalibrated logits under inference mode. Construct
inputs with the checkpoint vocabulary and encoder through the validated producer;
raw tensors alone cannot establish encoder or causal provenance. No prediction
example, label, input text/code, vector cache or optimizer state is bundled.

The format does not distinguish fitted weights from random initialization; the
owner must document how weights were produced. A round trip is software evidence,
not predictive accuracy, proven mastery or learning effectiveness. Hashes detect
changed declared content, not producer authenticity: only load trusted local
artifacts. Private model internals are not a hostile-code security boundary.

Publication is for a new destination with same-filesystem staging and a
cooperating-writer lock. Existing destinations/locks are preserved; validation,
serialization and rename failures clean owned staging/locks. Do not delete another
writer's lock. Uncooperative filesystem writers, process crashes, power-loss
durability and concurrent model mutation during save are outside this contract.
Generic API imports remain independent of this optional Torch module. No trainer,
training command, calibration, registry entry or serving activation is added.
