# Logistic historical baseline

`LogisticBaseline.fit(training_examples, C=1.0, max_iter=1000, seed=38)` uses
`historical-numeric-v1` features, fits StandardScaler on those examples only,
then fits L2-regularized scikit-learn logistic regression with LBFGS and fixed
tolerance 1e-8. Both outcome classes are required; convergence warnings fail
explicitly. Callers own partition membership and validation-only configuration
selection. Install the optional research dependencies to train.

`predict(examples)` returns uncalibrated `p(correct)` using saved means, positive
scales, coefficients and intercept; prediction labels are ignored. JSON loading
validates finite parameters, dimensions and exact feature order/version. No
pickle, executable deserialization or scikit-learn import is needed for inference.
Extreme finite scores use a stable sigmoid. Corrupt parameters producing a
nonfinite score fail. Model payloads record C, iteration limit and seed; artifact
provenance and training-run manifests are separate integration deliverables.

Synthetic tests verify arithmetic and reload parity, not measured predictive
quality, mastery or recommendation learning effectiveness. There is no target
code/text or candidate/student identity vocabulary in this baseline.
