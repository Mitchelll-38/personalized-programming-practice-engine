# Reproducible baseline smoke runs

Create a processing bundle with an explicit synthetic declaration, then run:

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.rates data/processed/day1 --output artifacts/runs/problem-rate-smoke --variant problem
```

The command verifies the processing hashes and split source/seed, checks disjoint
student groups and causal examples, fits only the train partition and evaluates
validation. It does not parse test examples or select parameters from test data.
Integrity verification hashes test bytes as part of the bundle; that is not test
evaluation. Existing run directories are rejected. Atomic directory replacement
publishes `model.json`, `validation.json` and `run.json` together.

Global and problem variants are separate declared runs. Manifests record smoothing,
seed, versions and source/split provenance. These runs exercise software only:
the current command deliberately requires synthetic input while real access,
terms and catalog/grading gates remain unmet. No fixture metric is a research
result or evidence of improved learning. The saved model does not activate the API.
