# Content training optimizer core

Owner: model platform engineer. Depends on merged content forward/checkpoint PRs
#53/#55. Purpose: fit the causal content LSTM on supplied training examples and
frozen entries, choosing the first best epoch by validation log loss. Acceptance:
training-only concept vocabulary; bounded deterministic CPU Adam/BCE mini-batches
with clipping; frozen input vectors; validation-only early stopping; restore best
weights and caller RNG/thread/determinism/default-device state, including failures.

Plan recorded before implementation: expose a typed bounded config and an in-memory
fit result (model, vocabulary, validation probabilities, aggregate epochs and best
epoch). Batch train and validation independently through the validated producer;
never instantiate an encoder or read test data. Preserve only exact best weights
on strict log-loss improvement, so ties retain the earliest epoch. Test repeated
seeds, causality/labels, unknown content, learning, selection/patience and failure
restoration. A separate dependent PR will verify bundles/caches and publish runs;
this core has no filesystem, CLI, downloads, checkpoint publication or activation.

`fit_content(train, validation, entries, encoder, config=ContentTrainingConfig())`
requires nonempty list/tuple partitions and exact supplied frozen-cache entries.
The caller owns split, source permission and partition verification; the separate
bundle command will enforce the synthetic-only research gate. This in-memory core
has no test partition argument and never instantiates an encoder or downloads data.

The concept vocabulary fits only supplied training targets/permitted histories.
Unknown tags are ignored reserved IDs; held-out exercise IDs have no embedding and
retain their actual candidate content signal. Examples are revalidated by the
causal batch producer, labels remain outside forward features, and input vectors
are detached. Adam updates only the learned projections/embeddings/LSTM/head using
candidate BCE, shuffled bounded mini-batches and norm clipping at 5. Validation is
batched independently under inference mode; only validation aggregate log loss
selects weights, with strict improvements retaining cloned state. Ties count
toward patience and keep the earliest best epoch. Returned model is in eval mode.

Configuration bounds match checkpoint dimensions; batch size is at most 256,
epochs/patience at most 500, and learning rate finite in (0,1]. Input dimension is
at most 4,096 and vocabulary size at most 10,000. Data/history size remains a caller
resource decision. One CPU thread, deterministic algorithms and seeded CPU RNG
are scoped to the fit, restoring prior RNG/thread/determinism/warn-only and default
device context on success or failure. CPU-only seeding avoids changing accelerator
RNG. Concurrent fits/global Torch setting changes in one process are unsupported.

`ContentFit` returns the selected model, training vocabulary, validation
probabilities, aggregate epoch losses and best epoch; these are in-memory values,
not a published research report. Original-synthetic tests demonstrate repeatable
optimization, label isolation and early stopping. No real-student results,
calibration, proven mastery or learning-effectiveness claims are established.
