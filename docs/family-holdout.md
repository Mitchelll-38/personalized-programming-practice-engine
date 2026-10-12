# Exercise-family holdout protocol

CLI integration owner: platform engineer (`api_engineer`). Purpose: persist the
existing family protocol through the processing CLI. Acceptance: student mode
remains the default, family groups are deterministic and label-independent,
held-out responses never enter histories, and invalid maps create no artifacts.
Dependency: the reviewed family builder; model training integration is separate.

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

Persist a family bundle with an independently audited JSON object mapping
problem IDs to family IDs:

```powershell
practice-data data/fixtures/synthetic.jsonl --split-protocol family --family-map local-families.json --synthetic --dataset-version synthetic-v1 --output data/processed/families
```

`--split-protocol student` remains the default. `--family-map` is required only
in family mode; duplicate JSON keys, invalid entries, missing observed problems
and fewer than three observed families fail before output files are written.
The raw mapping SHA-256 is recorded in both audit and split metadata, alongside
the input hash. The manifest declares `family-holdout-v1` and covers the same five
processing artifacts. Mapping IDs are not inferred from outcome labels.
The current rate-training CLI deliberately rejects family bundles; family-aware
training is a separate integration. Synthetic output is not a research result.
