# Scalar temperature calibration

Owner: coordinating engineer. Purpose: provide a small portable calibrator before
run/artifact integration. Acceptance: deterministic validation-only grid selection,
stable scalar inference, strict JSON and meaningful confidence/edge tests.
Dependencies: canonical prediction examples; no extra libraries or neural trainer.

`TemperatureScaler.fit_validation(validation_examples, validation_probabilities)`
chooses temperature by mean binary log loss over the predeclared grid
`(0.5, 0.75, 1, 1.5, 2, 3, 5)`. Inputs must be nonempty/aligned with both outcome
classes. The caller must supply predictions from a fixed model on validation only;
the function cannot authenticate partition membership. It never opens datasets.
Do not select the grid, model or temperature using locked test labels.

Inference clips probabilities to `[1e-6, 1-1e-6]`, converts them to logits, divides
by the fitted positive temperature and applies a stable sigmoid. Temperature above
1 softens confidence; below 1 sharpens it. There is no fitted bias, so probability
0.5 remains 0.5. Even temperature 1 clips endpoint probabilities. Equal objectives
prefer temperature closest to 1 in log space, then the smaller temperature;
input grid order is irrelevant. This is a simplified grid method, not a claim of
continuous maximum-likelihood optimization.

Portable JSON records the scalar, fixed clipping rule, version and declared
validation fit partition. It has no mutable model dictionary. Run integration must
bind this payload to the exact base-model and split hashes and record the fitting
grid before treating it as an activated calibrated artifact. This PR does not
change existing uncalibrated artifact flags or API predictions.

Fitting log loss and reliability on the same validation observations is descriptive
and optimistic. Assess selected calibration on untouched evaluation data; never
describe a fitted flag as proof that individual probabilities are reliable.
Only original synthetic software tests have been run. No real-data result is claimed.

## Validation input integrity fix

Owner: data/ML engineer. Purpose: prevent temperature selection from treating
unchecked copied labels as truth values. Acceptance: fitting rejects malformed
`PredictionExample` rows, including non-Boolean labels, blank student IDs and
invalid nested histories, before checking class balance; valid synthetic fitting
and portable prediction remain unchanged. Dependencies: the canonical schema
only. No private data, empirical result or partition policy changes are involved.
