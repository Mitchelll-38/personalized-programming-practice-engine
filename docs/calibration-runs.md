# Validation-only calibration runs

October 27 receipt integrity segment — Owner: data engineer. Purpose: bind the
calibration validation digest to the exact verified bytes consumed for fitting.
Acceptance: a synthetic validation-file mutation after bundle loading cannot
change the published fitting digest; ordinary calibration and artifact reload
still succeed. Dependency: the shared bundle loader's verified artifact hashes.
This check does not authenticate the source data or establish empirical quality.
The fitting record now uses the manifest digest checked against the same
validation bytes the bundle loader parsed. A synthetic regression changes the
file during fitting and confirms the artifact retains the consumed digest.
Focused calibration checks passed 16 tests on Windows; no real data was used.

Owner: coordinator. Purpose: reproduce scalar calibration on a fixed fitted
baseline without refitting the base model or touching locked test examples.
Dependencies: shared synthetic bundle boundary, portable baselines, temperature
scaling, reliability diagnostics and calibrated artifact envelopes. Acceptance:
exact base/split provenance, validation-derived fitting hashes, deterministic
reload parity, honest same-validation diagnostics and complete atomic publication.

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.calibration data/processed/day1 --base-model artifacts/runs/logistic-smoke/model.json --output artifacts/runs/logistic-calibration
```

The command accepts declared synthetic student/family bundles only. Base-model
provenance must equal the bundle's source/dataset/split record exactly. Only the
base model's validation predictions and validation labels fit the scalar; the
baseline is never refitted. A predeclared grid is recorded; the default matches
`TemperatureScaler`. Validation must contain both outcome classes.

`model.json` binds the embedded base artifact to validation-file bytes, the ordered
probability array and declared fitting grid/count. The probability digest is
`payload_hash({"probabilities": ordered_probabilities})`, using the shared canonical
JSON hash. The full base artifact hash includes its variant and provenance.
Predictions after artifact reload must match the in-memory scaled predictions.

`validation.json` contains before/after metrics; `reliability.json` contains
before/after fixed ten-bin diagnostics for both interaction and equal-student
weighting. These use the **same observations used to fit calibration**, so they
are optimistic descriptive fitting diagnostics, not independent calibration
evidence. No claim of improved predictive quality or learning follows.

`run.json` records model/hash/split/config/seed/count information and explicitly
marks synthetic output, validation fitting/evaluation and `test_evaluated=false`.
The shared loader parses train/validation and integrity-hashes test bytes without
parsing test examples. All four files publish together through staged directory
replacement; existing outputs are rejected and failures clean staging. Concurrent
writers to one destination are unsupported; use unique run paths.

This workflow does not activate an API model. Existing research routes still
reject calibrated envelope versions until a separate reviewed integration. Keep
artifacts local and ignored. Real data, catalog/grading audits and locked-test
evaluation remain separate gates; only synthetic software tests have run.
