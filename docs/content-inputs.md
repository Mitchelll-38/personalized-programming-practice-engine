# Content-aware batch foundation

Owner: model platform engineer. Purpose: establish causal frozen-vector inputs and
a training-only concept vocabulary before the separate content-aware LSTM forward
PR. Dependency: frozen extraction/cache contract PR #45. Acceptance: exact cache
role/content/config validation; no target response in forward inputs; strict causal
histories; right padding; explicit missing-code/unknown tags; detached vocabulary
serialization; and labels held separately from input tensors.

Plan: fit a sorted immutable concept vocabulary on supplied training examples;
revalidate canonical examples and label-free timing; retrieve only matching frozen
statement/historical-code cache entries; build padded tensors and a separate target
tensor. Tests vary target labels, candidate IDs, future history, metadata integrity,
missing code and unseen concept tags. No model training or forward layer is claimed
by this PR. The coordinator owns chronological progress records.

`ConceptVocabulary.fit(train_examples)` uses only candidate/permitted-history tags
in the examples supplied as training data. The caller owns partition membership.
The sorted immutable names assign known IDs from 2; 0 is PAD and 1 is UNK. Strict
JSON round trips preserve order/IDs without sharing mutable lists. Validation and
test tags do not extend the fitted vocabulary. The later forward network will
ignore UNK tags in its known-concept mean; this batch builder does not pool tags.

`make_content_batch(examples, vocabulary, entries, encoder)` accepts a mapping of
entry key to reviewed `EmbeddingEntry`, such as the entries returned by frozen
extraction. It revalidates canonical examples, label-free causal timing and cache
metadata before copying vectors to finite float32 tensors. Entries must bind exact
allowed content, role and encoder configuration. Hashes validate declared integrity,
not producer authenticity; keep real derived vectors private and use trusted caches.

`ContentInputs` contains right-padded historical problem/code vectors `[B,T,D]`,
code-present flags `[B,T]`, concept IDs `[B,T,K]`, prior correctness `[B,T]`, observed
lengths `[B]`, candidate problem vectors `[B,D]` and candidate concept IDs `[B,K]`.
`T` and `K` are at least 1. Padding vectors/IDs are zero; missing/blank historical
code gets zero vectors with an explicit false flag. Candidate code/outcomes and
student/problem-ID embeddings have no input field. A cold learner has length 0;
unknown exercises still retain their supplied statement/concepts. `ContentBatch`
holds a separate target-label tensor, never passed to the future forward method.

The builder performs no network/file reads or encoder training. Tensor inputs
have no encoder gradient graph. The forward PR must mask arbitrary padded values
before projection/embedding, pack observed lengths and detach frozen vectors before
learned projections. This foundation alone does not predict correctness or establish
content quality, mastery or learning effectiveness. Unit tests use original manually
provided synthetic vectors; real CodeBERT execution is recorded separately from
this contract under ignored private storage.
