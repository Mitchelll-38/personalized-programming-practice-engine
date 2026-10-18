# Temperature-calibrated baseline artifacts

Owner: coordinator. Purpose: bind the portable scalar calibrator to the exact
base model and validation fitting record before separate run/API integration.
Dependencies: reviewed rate/logistic/BKT JSON artifacts and temperature scaling.
Acceptance: strict JSON, matching base/split provenance, declared validation hashes
and grid, live integrity checks, prediction/reload parity and atomic persistence.

The envelope embeds an uncalibrated baseline and scalar payload. It records a hash
of the entire base artifact, including its variant and provenance, and a checksum
over the complete calibrated envelope. Its validation record includes the exact
validation-file hash, probability-array hash, example count and predeclared grid.
Record provenance must match the base artifact, and selected temperature must
belong to that grid. Unknown versions, unsupported models, malformed grids,
provenance mismatches and changed nested payloads fail validation.

`save_calibrated_artifact` writes detached JSON with same-directory atomic
replacement. `load_calibrated_artifact` revalidates the envelope; `predict` checks
live integrity before applying temperature scaling to the embedded baseline.
No pickle, optional training-library imports or neural model loading is involved.

The writer does not fit a calibrator or open a dataset. Callers must supply an
honest validation record from fixed-model predictions; hashes detect corruption,
not authorized use, partition membership or model quality. `calibrated=true` means
the declared scaling method is applied, not that probabilities are proven reliable.
Fitting and measuring calibration on the same validation observations is optimistic.
Keep locked tests untouched until selection is complete.

This change does not modify baseline artifacts, the generic loader, API acceptance
or the learner dashboard. Existing API routes still require uncalibrated baselines;
calibration run/activation follows in separate reviewed PRs. Tests use original
synthetic examples only. Persist generated artifacts inside ignored project folders.
