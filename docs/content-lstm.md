# Content-aware LSTM forward foundation

Owner: model platform engineer. Purpose: combine frozen statement/code features,
training-only concepts and prior outcomes in a causal candidate-conditioned LSTM.
Dependency: content batch/vocabulary PR #49. Acceptance: candidate text/concepts
without target response; packed observed prefixes; zero cold state; ignored padding
and missing-code sentinels; zero unknown-concept representation; frozen input
gradients; finite logits and strict shape/type checks.

Plan: project frozen problem/code vectors, pool known concept embeddings and embed
historical correctness; pack observed interactions through one LSTM; concatenate
the final state with candidate problem/concept features for a scalar head. Validate
inputs before indexing and mask padding before transforms. Test batch isolation,
padding/cold/unknown/missing behavior, target-label separation, candidate content
conditioning and projection-only gradients. No trainer/checkpoint/API or measured
predictive benefit is added. The coordinator owns chronological records.

`ContentLSTM(concept_vocabulary_size, input_size=768, ...)` returns one correctness
**logit** per example from `ContentInputs`. Supply only a training-fitted vocabulary
and validated frozen-vector batches from [content-inputs.md](content-inputs.md).
Problem vectors share a learned projection for history and candidate; historical
code has a separate learned projection. Interaction inputs concatenate these,
known-concept means, prior correctness embeddings and the code-present flag.
The candidate head combines the final history state with candidate text/concepts.
There is no exercise/student identity vocabulary, candidate code or target label.

Only observed prefixes enter packed recurrence. A learner with length 0 has a zero
history state and a candidate-dependent population prediction, not personalized
evidence. Missing historical code contributes a zero projection plus false flag.
Concept IDs 0/1 (PAD/UNK) contribute exactly zero and do not dilute known-concept
means, avoiding a random untrained UNK embedding. Unseen exercises retain their
supplied content. All-unknown concepts still retain the candidate text signal.

Padding/missing-code values are masked before projections and embedding lookup;
arbitrary padded NaNs/invalid IDs cannot affect observed logits. Observed vectors,
IDs, types, shapes, lengths and model device/dtype must be valid. The model detaches
frozen vectors but trains its projections, concept/correctness embeddings, LSTM
and head. Target labels remain outside `forward`. Raw tensors cannot authenticate
their causal provenance; use the validated batch producer and trusted caches.

This is a forward/gradient foundation with randomly initialized parameters. It has
no fitted checkpoint, optimizer, early stopping, training command, calibration or
serving activation. Finite synthetic outputs demonstrate software behavior only,
not content quality, proven mastery, predictive accuracy or learning improvement.
The default feature dimension matches frozen CodeBERT; small explicitly synthetic
dimensions are used in unit tests. Actual cached synthetic CodeBERT vectors are
reserved for a separate private smoke receipt, never empirical student evaluation.
