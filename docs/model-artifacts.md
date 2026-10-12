# Rate baseline artifacts

`save_rate_artifact` / `load_rate_artifact` use strict versioned JSON with a
validated count-model payload and SHA-256 consistency check. No pickle or
executable deserialization is used. The global/problem variant, feature/model
versions, dataset declaration, source hash, split version/hash and train-only fit
partition are recorded. Predictions after reload match the original fitted model.

The provenance is a declaration supplied by the training workflow, not proof of
permission, training partition membership or model quality. Hashes detect
accidental payload changes; they do not authenticate the artifact's author.
Synthetic artifacts remain synthetic and uncalibrated, with no research claims.

Saving uses a same-directory temporary file and atomic replacement so an
interrupted write does not leave a partially serialized active artifact. Keep
artifacts in ignored `artifacts/`; saving a research model does not make it the
active demo API model. API selection is a separate reviewed integration.

Historical logistic and shared BKT models use a separate portable-baseline JSON
envelope with the same provenance, payload hashing, live-mutation rejection and
atomic writer. `load_baseline_artifact` dispatches only known envelope versions;
model/feature versions must match the fixed internal registry. Inference imports
no optional training library. Rate artifacts remain backward compatible.
