# Shared-parameter BKT baseline

`models.bkt.BKTBaseline.fit(training_examples, parameter_grid=None)` selects one
parameter set shared across all concepts using the smallest mean conditional
binary log loss on supplied **training** examples. This is a small grid-likelihood
baseline, not per-concept EM fitting. The default 24 configurations combine
initial={0.2,0.5}, learn={0,0.1,0.2}, guess={0.1,0.2}, slip={0.1,0.2}. Equal losses
use lexicographic parameter order. Optional grids are training search configs;
callers must record their grid and split provenance in run manifests.

Each concept starts at `initial`. For every permitted earlier first-attempt
response, apply classic Bayesian conditioning using guess/slip, then learning:
`posterior + (1-posterior)*learn`. There is no forgetting. A historical response
with several tags independently updates each tagged concept. Candidate success
is the mean of distinct candidate concept probabilities
`posterior*(1-slip) + (1-posterior)*guess`. Unknown concepts use the shared initial
prior; no concept vocabulary is fitted. This multi-concept rule is a modeling
simplification, not proof of independent skills or measured mastery.

Initial/learn lie in [0,1]; guess/slip lie strictly in (0,1) and sum to less than
one. Positive observation noise prevents undefined conditioning on zero-likelihood
responses. Fitting log loss uses fixed 1e-15 clipping. Prediction validates the
same causal history boundaries as historical features and ignores target labels,
target text and submitted code. The versioned JSON payload contains only strict
parameters, not student responses. CLI/API integration and empirical evaluation
remain separate PRs; callers own validation/test access and approved real data.
