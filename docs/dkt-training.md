# Synthetic CPU DKT training

Owner: engineer C. Purpose: join the verified synthetic bundle and checkpoint
interfaces in one bounded CPU training workflow. Dependencies: shared bundle
validation and DKT checkpoint PR #26. Acceptance: train-only vocabulary, candidate
loss, deterministic seeded runs, validation early stopping, reload parity and
no parsing of test examples. Calibration, serving and real-data training are
separate changes. The coordinator maintains the chronological progress ledger.

Implementation plan: validate configuration and the synthetic bundle; fit exercise
IDs on training examples; optimize candidate BCE in shuffled mini-batches; retain
the best state by validation log loss; atomically publish the selected checkpoint,
validation metrics and run metadata. Tests cover deterministic repetition,
patience, causal histories, poisoned test bytes and failed publication.

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.dkt data/processed/day1 --output artifacts/runs/dkt-smoke --seed 38 --max-epochs 30 --patience 5
```

Install the optional pinned CPU Torch environment first. The command supports
student and family holdouts through the shared bundle validator, but accepts only
declared synthetic data. Epochs, batch size and layer dimensions have explicit
positive upper bounds; learning rate must be finite in `(0, 1]`. Prefix memory
cost grows with history lengths: bounded hyperparameters do not bound dataset size.
This small CPU workflow is not an efficient full-release trainer.

Exercise IDs fit only training candidates and permitted histories. Adam optimizes
one BCE target per example, from the selected candidate head, with gradient norm
clipped at 5. Padding has no targets and no loss. Validation never runs backward.
Strictly lower aggregate validation log loss selects a cloned checkpoint; ties
keep the earlier epoch. Stop after `patience` consecutive non-improving epochs or
the epoch limit. Unknown validation candidates use the Beta(1,1) training-population
fallback, not an untrained UNK neural head. Consequently an ID-only model under
family holdouts produces population-rate predictions and often stops on a plateau.
This is an explicit limitation, not evidence of generalization to new exercises.

One CPU thread, a seeded RNG and deterministic Torch algorithms cover training and
reload verification. The caller's CPU RNG, thread count and determinism settings
are restored afterward; concurrent in-process training is unsupported because
Torch settings are process-global. Reproducibility is scoped to the pinned software
and compatible CPU environment, not arbitrary versions or hardware.
Training also pins the CPU device while constructing the model and batches, so an
outer Torch default-device context does not change the run or its checkpoint.

Each new run directory contains `model/weights.pt`, `model/metadata.json`,
`validation.json` and `run.json`. A staging directory and cooperating-writer lock
publish them together without replacing an existing run. Failures clean staging;
abrupt process termination can leave a lock requiring manual cleanup. Selected
checkpoint validation predictions must equal in-memory predictions before rollout.
The run records config, Torch version, hashes, partition provenance, example counts,
epoch losses and selected epoch. Test bytes are integrity-hashed but never decoded
as examples. Synthetic validation metrics are software smoke evidence only:
`research_results=false`, `test_evaluated=false`, `calibrated=false`. No API model
activation, real-data training, calibration or learning-effectiveness claim follows.

## October 18: bounded validation and reload plan

Owner: platform engineer. Purpose: remove whole-validation padded tensor allocation
from the training workflow and selected-checkpoint reload check. Dependencies:
existing DKT forward/checkpoint interfaces and the optional pinned CPU environment.
Acceptance: every validation/reload call uses at most the configured `batch_size`;
ordered probabilities, unknown-candidate population fallback, aggregate log-loss
selection and selected-state reload parity remain intact, including a short final
batch. Synthetic-only bundle validation and unread test examples remain required.

Implement sequential validation slices and checkpoint reload slices using the
existing training batch limit. Verify parity against whole-batch predictions,
unequal final chunks, batch allocation limits and the existing deterministic,
early-stopping, publication and poisoned-test regressions. This bounds rows per
padded tensor, not history length, total dataset memory or elapsed run time; it does
not approve a real-release resource budget or enable real training.

Validation and selected-checkpoint reload now use sequential slices of at most
`batch_size` examples. Ordered scalar predictions are collected before aggregate
metrics are computed, so a short last slice has its proper example weight. Reload
uses the same slice boundaries as in-memory validation for exact selected-state
parity. Tensor allocations scale with each slice's longest history; the loaded
partitions and scalar probabilities still occupy memory for the full dataset.
Changing batch size may produce ordinary floating-point differences and is not a
promise of bitwise equivalence across configurations. Checkpoint inference outside
this training workflow retains its caller-supplied batch interface.

## Direct DKT input validation fix

Owner: data/ML engineer. Purpose: reject unchecked copied outcomes before DKT
vocabulary fitting, training counts or BCE batches can use them. Acceptance:
direct vocabulary fitting and batch construction reject noncanonical examples,
non-Boolean labels and invalid copied nested fields; direct training fails before
model construction, while valid synthetic training and label-free forward parity
remain unchanged. Dependencies: the canonical schema and existing DKT path only.
No private data, test-partition access or empirical claim is involved.

## CPU construction under alternate default devices

Owner: model engineer. Purpose: make the declared CPU DKT trainer independent of
the caller's Torch default device. Acceptance: an original synthetic bundle
trains under a `meta` default-device context with the same run and checkpoint
predictions as a normal CPU call; the caller's default device and CPU RNG remain
unchanged on return. Dependencies: the existing bounded DKT trainer and strict
CPU checkpoint loader. Scope is training context only; checkpoint semantics and
the published run format are unchanged.
