# Historical numeric feature contract

`models.features.historical_features(examples)` returns six floats in
`FEATURE_NAMES` order with version `historical-numeric-v1`:

1. `log1p` prior first-attempt count.
2. Prior success rate with fixed Beta(1,1) smoothing.
3. `log1p` count of the five most recent observed first attempts.
4. Recent success rate with the same smoothing.
5. `log1p` count of prior interactions sharing at least one candidate concept.
6. Success rate for those interactions with the same smoothing.

An interaction matching multiple candidate concepts counts once. Empty evidence
has count zero and success estimate 0.5. Candidate labels/text, submitted code,
student identity and problem-ID vocabularies are excluded. Concept names provide
only equality matching; there is no learned concept vocabulary or preprocessing.

Each history must contain distinct first attempts from the same student, strictly
ordered before the target, and exclude the candidate exercise response. Invalid
direct examples fail. Features represent available observed evidence, not proven
mastery. Held-out-student and exercise-family protocols supply different allowed
histories; this function does not choose a partition or certify dataset provenance.
Train-only scaling and logistic fitting belong to the next independent model PR.

## Direct prediction input integrity fix

Owner: data/ML engineer. Purpose: reject unchecked copied historical outcomes
before they change logistic features or BKT predictions. Acceptance: feature
extraction and both direct model prediction paths reject noncanonical examples
and invalid nested interactions, while valid synthetic features and predictions
retain their existing values. Dependency: the canonical schema only; no bundle,
policy, private data or partition behavior changes are involved.
