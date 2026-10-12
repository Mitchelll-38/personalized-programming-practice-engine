# Exercise-family holdout protocol

`practice_engine.data.holdouts.family_holdout(rows, problem_families, seed=38)`
returns a `FamilyHoldout` with `metadata` and train/validation/test `examples`.
Callers supply a verified problem-to-family mapping to keep variants and near
duplicates together. Missing mappings, empty family IDs and fewer than three
observed families fail. Unobserved mapping entries do not affect allocation.

Allocation uses sorted observed family IDs and a local seeded shuffle. Requested
ratios are 70/15/15, with at least one family in every partition; small groups may
differ from these ratios. Metadata records exact family/problem groups, the
observed mapping, seed, protocol version and history policy. Freeze and persist
this metadata before evaluating models. Adding families can change allocations.

All examples use only earlier first-attempt responses to **training exercises**
in their own student's history. Validation/test responses, labels and submitted
code never enter histories, even when those responses chronologically precede a
training target. Target labels remain separate from candidate statement/concepts.
The existing strict ordering and retry checks apply before partition construction.

This builder does not fit vocabularies, infer families or certify real-data terms.
Training consumers must fit their exercise vocabulary on the training partition,
map held-out exercise IDs to unknown, and fit transforms on training only. It is
an explicit exercise-holdout protocol, separate from held-out-student evaluation
where earlier observed student prefixes may remain available.
