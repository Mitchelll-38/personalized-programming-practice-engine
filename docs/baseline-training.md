# Logistic and BKT validation runs

Owner: baseline engineer. Purpose: make the fitted portable baselines reproducible
from a verified processing bundle. Acceptance: train-only fitting, validation-only
metrics, exact prediction parity after artifact reload, atomic publication and
recorded configuration/provenance. Dependencies: shared bundle validation (PR
#25), portable logistic/BKT artifacts (PR #21). Rates keep their existing command.

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.baselines data/processed/day1 --output artifacts/runs/logistic-smoke --model logistic --C 1 --max-iter 1000
.\.venv\Scripts\python.exe -m practice_engine.training.baselines data/processed/day1 --output artifacts/runs/bkt-smoke --model bkt
```

Use the pinned research environment for logistic fitting. Both commands require
declared synthetic input and accept student or family processing bundles through
`load_training_bundle`. The shared boundary verifies integrity, partition
membership and causal histories; family histories contain only training exercises.
Test files are hashed for integrity but never parsed or evaluated.

Logistic fits its scaler and regression on train only, uses the processing seed,
and requires both training outcome classes. `C` must be positive and finite;
`max-iter` must be a positive integer. Nonconvergence fails before publishing a run.
BKT uses one parameter set shared across concepts and selects minimum train
conditional log loss from 24 configurations: initial probability {0.2, 0.5}, learn
{0, 0.1, 0.2}, guess {0.1, 0.2}, slip {0.1, 0.2}. Ties use lexicographic parameter
order. There is no forgetting; multi-tag observations update concepts independently
and candidate probabilities average distinct concepts. Logistic options are rejected
for BKT rather than silently ignored. No parameters are selected using validation.

Each new run directory receives `model.json`, `validation.json` and `run.json`
together through atomic directory replacement. The command reloads the JSON artifact
and requires identical validation predictions before publishing. Existing output
directories are rejected; failures discard temporary files. Concurrent writers to
the same destination are unsupported; use separate run paths.

The run records model/feature/artifact versions, model payload hash, configuration,
seed, example counts, processing-manifest hash and source/split provenance. Metrics
include aggregate and equal-student summaries from the shared evaluator. All runs
are explicitly synthetic, uncalibrated, validation-only software checks, with
`research_results=false` and `test_evaluated=false`. They are not real-data results,
proven mastery or evidence of improved learning. Saved artifacts do not activate
the replay API. Real-data permission/catalog gates, DKT and calibration are separate
work units.
