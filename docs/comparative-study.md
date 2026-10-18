# Comparative study protocol

Owner: coordinator/data lead. Purpose: specify model selection before real
validation results exist. Acceptance: fixed comparison objective, split/seed and
budget policy, calibration separation, locked-test release checklist and explicit
unimplemented work. Dependencies: reviewed chronology/import/provenance and
permitted private data; none is waived by this document.

Plan recorded October 18, 2026: inspect existing trainers and metric contracts;
define the smallest common experiment schedule; obtain independent review before
any real-data run. This is a prospective protocol, not a completed experiment or
an executable real-data runner. All current bundle commands remain synthetic-only.

## Freeze before validation

The primary task is correctness on the first scored attempt, using only strictly
earlier observed first-attempt history and candidate statement/concepts. Archive
challenge labels and course grades are not the target. Keep acquired and derived
student records private. A comparison record must bind:

- Archive, table, catalog, mapping and canonical hashes; permission evidence;
  source-backed timezone/tie/exclusion policy and counts before/after exclusions.
- Exact code/environment revisions and machine; a reviewed real-source manifest
  and loader path, without relabeling actual data as synthetic.
- One frozen 70/15/15 student partition with split seed 38, reusing identical
  examples for every primary model. Earlier observed held-out-student prefixes
  are allowed by this protocol; future interactions are never allowed.
- A separate family holdout only after a label-blind, reviewed near-duplicate
  family map exists. Its histories contain training-exercise responses only,
  as specified in [family-holdout.md](family-holdout.md). Do not pool protocols
  or claim family generalization from the student experiment.

Exact assignments/counts and any resource-driven protocol amendment need a dated,
reviewed record before inspecting real validation metrics. Do not derive family
groups from outcomes, use official early/late files as our frozen partitions, or
silently retain only the easiest-to-order learners. Report unresolved exclusions.

## Initial comparison and resource gate

Use one declared configuration per model; no validation hyperparameter search in
this initial comparison. Baseline fitting and neural early stopping remain as
implemented. Proposed configurations to freeze in the run record:

| Model | Configuration | Fit/selection rule |
|---|---|---|
| Global and problem rate | Smoothing alpha 1 | Training outcomes only; unknown problems use global rate |
| Logistic | C 1, max_iter 1000 | Train-only scaler/features; nonconvergence fails |
| BKT | Existing fixed 24-configuration grid | Minimum training conditional log loss; fixed lexicographic ties |
| DKT | Embedding 16, hidden 64 | Adam, learning rate .01, batch 32, at most 30 epochs, patience 5 |
| Content LSTM | Projection 32, concept 16, correctness 8, hidden 64 | Same optimizer/rate/batch/epoch/patience budget as DKT |

Neural seeds are 38, 39 and 40 with the same split; deterministic models run once.
Keep every seed result, including failures. Both neural trainers select strict
aggregate validation log-loss improvements and retain the earliest tied epoch.
Matching epoch/hidden budgets does not equate parameter count, wall time or FLOPs;
report actual parameter counts, epochs, elapsed training/embedding time and memory.
Unknown-ID DKT family predictions use the documented population fallback.

Before any full run, measure train-only shapes/history lengths, cache size and a
bounded training pilot on the available local CPU. Record machine and peak memory,
then freeze an explicit per-run wall-time/memory ceiling and total experiment
budget in a reviewed amendment. **No numeric resource ceiling is approved yet.**
No paid compute, GPU availability or full-release feasibility is assumed. Existing
DKT validation batching can materialize a whole partition; a pilot must account
for this before launch. No run starts until the resource amendment is merged.
Stop exhausted runs, retain failure records, and report the comparison incomplete
rather than selecting the most favorable completed seed or extending its budget.

Content uses the pinned frozen encoder and exact cache manifest in
[codebert-extraction.md](codebert-extraction.md); no encoder fine-tuning. The first
comparison uses statement, permitted historical code and concept inputs. Ablations
need their own predeclared feature-mask implementation/configuration and resource
amendment before results are inspected; they are not implemented or completed here.

## Validation decision and calibration

Primary ranking is mean aggregate validation log loss across the three declared
neural seeds (one value for deterministic baselines). Lower wins. Use the exact
metric definition in [evaluation-metrics.md](evaluation-metrics.md). Report all
individual seed values, equal-student log loss/Brier, aggregate Brier, ROC AUC and
incorrect-positive average precision alongside counts/prevalence. Undefined
one-class ranking metrics stay null with reasons. These are repeated fits on one
split, not independent population replications.

An incomplete three-seed neural model cannot win this declared comparison; report
it separately as incomplete. For exact primary-score ties use this fixed order:
global rate, problem rate, logistic, BKT, DKT, content. Do not select using test
metrics, calibration-fit diagnostics or whichever secondary metric looks best.
For a selected neural family, deployment uses its seed-38 checkpoint, chosen in
advance rather than choosing the luckiest seed. Report that checkpoint's metrics
separately from the family mean; an ensemble is a separate change.

Select the uncalibrated base family first. Only then fit a scalar on its validation
predictions, freeze the calibrated artifact/grid/hash, and retain the uncalibrated
artifact for comparison. Same-validation before/after figures are fitting
diagnostics, not independent evidence of calibration improvement. The current
[calibration runner](calibration-runs.md) supports synthetic portable baselines;
real-source and neural calibration envelopes require separate reviewed PRs.

## Locked-test release

Before test examples are decoded, review a selection record binding the selected
family/checkpoint, completed and failed runs, all frozen baseline artifacts,
calibrator if supported, split hashes and the planned report. Integrity-hashing
test bytes earlier is permitted; reading test examples for tuning is not.

A separate reviewed evaluator must score the frozen baselines and selected
checkpoint together once, including calibrated and uncalibrated versions if
available. Report every declared comparator and the selected checkpoint's metrics,
sample/student counts, unknown-ID coverage and history-length strata (0, 1-4,
5-19, 20+). Uncertainty should resample whole students with fixed seed 38 and
1,000 paired bootstrap replicates, report 95% percentile intervals, and identify
undefined/sparse estimates. The [paired student bootstrap](student-bootstrap.md)
implements log-loss/Brier intervals; a locked-test evaluator and ranking-metric
intervals remain unimplemented.
Family results are a separate report if that protocol clears its own gates.

Never revise features, seeds, calibration or selection after test inspection.
Any defect requiring rerun must identify the invalidated report and correction;
the replacement is not an untouched-test experiment. Keep row-level predictions
private. Publishing aggregate reports or model artifacts requires a separate
rights review. Offline predictive scores and replay behavior do not establish
improved learning, proven mastery or recommendation effectiveness.
