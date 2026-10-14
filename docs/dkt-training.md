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
