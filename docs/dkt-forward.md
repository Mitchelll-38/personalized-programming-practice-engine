# Causal DKT forward pass

Owner: engineer C. Purpose: provide a small LSTM DKT input/forward boundary for a subsequent training PR. Dependencies: canonical prediction examples, shared causal-history validation, and the optional CPU PyTorch foundation (PR #18).

Acceptance criteria:

- Fit exercise vocabulary on training examples only; PAD=0, UNK=1, known IDs start at 2. Reject malformed/noncontiguous vocabulary JSON.
- Embed only prior exercise/outcome pairs; candidate IDs index the output head. Candidate labels remain in a separate batch field.
- Pack positive history lengths, exclude padding from recurrence, and use zero hidden state plus output bias for cold starts.
- Verify target-label and unrelated future-row invariance, padding invariance, unknown IDs and invalid causal histories.

`ExerciseVocabulary.fit(train_examples)` cannot infer split membership: callers must pass only the approved training partition. `make_batch(examples, vocabulary)` validates histories through the shared historical-features boundary. `DKT.forward(batch.inputs)` returns correctness **logits** for each candidate; use sigmoid for uncalibrated probabilities and BCE-with-logits for a later training loss. Labels never enter `DKTInputs`.

The forward pass is independent per batch row; it does not carry state across examples. Unknown histories and candidates map to UNK. Unknown candidate predictions share an output head. Cold-start predictions use a per-exercise bias without observing the candidate outcome. Text, code and concept embeddings are intentionally absent from this ID-only DKT baseline.

This PR contains no trainer, optimizer, checkpoint serialization, API rollout or empirical results. Tests use synthetic examples and randomly initialized CPU models. Real-data access and research evidence remain separate gates.
