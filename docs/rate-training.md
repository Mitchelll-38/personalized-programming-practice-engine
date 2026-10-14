# Reproducible baseline smoke runs

Owner: platform engineer. This change extracts a shared synthetic training-bundle
boundary and extends rate runs to reviewed family splits. Acceptance: verify
partition provenance, reject malformed or leaking histories before fitting,
preserve student runs and never parse test examples. Dependencies: processing
manifests and the family CLI. Logistic/BKT run commands remain separate work.

Create a processing bundle with an explicit synthetic declaration, then run:

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.rates data/processed/day1 --output artifacts/runs/problem-rate-smoke --variant problem
```

The command verifies the processing hashes and split source/seed, checks disjoint
student or exercise-family groups and causal examples, fits only the train partition and evaluates
validation. It does not parse test examples or select parameters from test data.
Integrity verification hashes test bytes as part of the bundle; that is not test
evaluation. Existing run directories are rejected. Atomic directory replacement
publishes `model.json`, `validation.json` and `run.json` together.

Global and problem variants are separate declared runs. Manifests record smoothing,
seed, versions and source/split provenance. These runs exercise software only:
the current command deliberately requires synthetic input while real access,
terms and catalog/grading gates remain unmet. No fixture metric is a research
result or evidence of improved learning. The saved model does not activate the API.

`load_training_bundle` returns train/validation examples, the verified manifest,
split metadata and artifact provenance. Family runs accept `family-holdout-v1`
bundles from the [family CLI](family-holdout.md), require exact disjoint
family/problem groups and map-hash agreement, and reject any history response
outside training families. Only train and validation examples are parsed;
test bytes are checked for integrity without consuming labels. Student histories
remain student-specific causal prefixes. Hashes do not certify usage rights.
