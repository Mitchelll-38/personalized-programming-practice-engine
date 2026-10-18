# Continuing sprint implementation

The user requests continuous progress across planned days. Complete and review small changes, integrate them, then advance to the next dependency-ready task. Day numbers organize reporting, not stopping points. Existing real-data access/terms and catalog verification gates remain open; synthetic smoke runs must never be presented as research evidence.

## Foundation changes (initial execution plan)

| Owner | PR-sized change | Acceptance | Dependency |
|---|---|---|---|
| Data engineer | Explicit exercise/family holdout partition builder | Exercise families disjoint; no held-out target response in training or primary scored histories; splits independent of labels | Canonical interactions |
| Model engineer | Global and smoothed problem-rate baselines | Fit on training examples only; cold start/unknown fallback; deterministic JSON round trip | PredictionExample contract |
| Coordinator | Baseline artifact format + package registration | Strict versioned JSON; no pickle; reload parity; explicit synthetic/unverified provenance | Rate-model interface |
| Model engineer | Historical features and logistic regression | Counts/recent/concept features depend only on prior history; train-only preprocessing; saved parameters | Feature contract and research dependencies |
| Data engineer | Evaluation metrics and student summaries | Probability metrics/incorrect-positive PR-AUC defined; one-class metrics explicit; grouped summaries | Baseline prediction interface |
| Coordinator | Reproducible training/evaluation command and run manifests | Verify preprocessing hashes; tune/evaluate validation only by default; keep test untouched; record configs/seeds | Models, metrics, artifacts |

Other product, BKT, neural, calibration and release tasks follow in their own reviewed PRs once these foundations are integrated. Do not bundle multiple rows into a day-sized PR.

## October 14 execution snapshot and planned segments (historical)

The foundations above are integrated. Logistic/BKT and CPU DKT run commands now
exercise synthetic train/validation bundles; the research API serves reviewed
synthetic JSON baselines opt-in. These software milestones do not complete the
real-data or learning-effectiveness gates. Exact merged changes and review fixes
are tracked in [progress.md](progress.md).

| Owner | Next PR-sized change | Acceptance | Dependency / gate |
|---|---|---|---|
| Model engineer | Frozen embedding-cache boundary | Exact content/config hashes, finite vectors, strict integrity, private atomic persistence; original synthetic vectors only | Active independent cache implementation; actual encoder follows separately |
| Product/platform engineer | Optional fitted-baseline inspector | Label-free next-distinct-exercise query, cancellation, clear synthetic/uncalibrated metadata, independent failures | Research API #32; active separate frontend work |
| Coordinator | Calibrated baseline artifact envelope | Bind scalar payload to exact base model and split; validation fitting record; strict live integrity and reload parity | Temperature #27 and portable artifacts; no automatic API activation |
| Model engineer | Frozen CodeBERT extraction adapter | Verified repository revision/license, explicit tokenization/truncation/pooling and reusable private cache | Cache boundary; optional dependencies and weights verified before use |
| Model engineer | Content-aware causal LSTM | Candidate statement/concepts and only prior responses; sequence masks; train-only learned vocabularies | Verified encoder/cache contract and DKT training foundation |
| Coordinator | Calibration run command | Fixed-model validation predictions only, fitting hashes/config, honest before/after diagnostic record, test untouched | Calibrated envelope and baseline run commands |
| Product/platform engineer | Recommendation event records | Log candidates, predictions/model/policy versions and selected exercise separately from later outcome | Explicit policy contract and SQLite migration; no learning-effect claim |
| Coordinator / data lead | Valid release receipt and actual audit | Valid private archive/checksum, terms/catalog/grading/time metadata reviewed before import | Official downloads currently zero-byte or timed out; no raw data in git |

Later locked-test comparisons, ablations, uncertainty analysis and real-data
reports remain gated on verified data/content and model selection. Do not replace
these deliverables with synthetic metrics. Continue dependency-ready software
work and reviewed small PRs while recording the unresolved gate.

## Research interfaces for the next PRs

- Canonical `PredictionExample` contains prior first-attempt `history`, candidate metadata and a separate `label`.
- New research model modules live in `src/practice_engine/models/`; they never import demo API heuristics.
- Rate model: `RateBaseline.fit(examples, alpha=1.0)`, `predict(examples, per_problem=True) -> list[float]`, `to_dict() -> dict`, `from_dict(payload) -> RateBaseline`. Require nonempty train set and positive finite smoothing; unknown exercise falls back to global smoothed rate.
- Research artifacts wrap a JSON-serializable model payload with its model type/version and dataset/split/feature provenance. A saved model is not automatically the active API model.
- Holdout module lives under `data/` and returns partition metadata plus partitioned examples. Holdout histories exclude all validation/test exercise responses across all groups, including earlier held-out responses in later scored histories. Student holdouts keep observed test prefixes allowed under their separate protocol.
- Initial metrics live under `evaluation/`; accept examples and probabilities, and do not choose thresholds or calibrators using test data.


## October 17 current segments

The historical table above records the earlier plan. Cache, inspector, calibrated
envelopes/run/API, encoder environment/extraction and recommendation generation
are now merged; see the chronological ledger and linked PRs. The following work
has distinct owners and review boundaries:

| Owner | Segment | Acceptance | Dependency |
|---|---|---|---|
| Coordinator/data lead | Verified real release receipt and audit | Nonempty permitted archive, hash/terms, actual catalog/grading/order review and locked import counts | DataShop sign-in and working browser download |
| Model engineer | Fair comparative validation and selection | Fixed real splits/seeds/budgets, baselines/DKT/content and feasible ablations; validation-only selection/calibration | Verified real data/catalog; actual compute budget |
| Product engineer | Selected-model results/probes and final rehearsal | Evidence-based model/result presentation, fixed concept probes, final reproduction guide | Actual comparisons/calibration and selected serving contract |


Choice-to-attempt backend/UI (#56/#57), strict checkpoints (#55), cache preparation
(#58), optimizer/run (#59/#60), configured policy/backend UI (#61/#62), local
containers/CI (#63/#65), loaded-content adapter/profile (#66/#68), walkthrough
(#67) and focused secondary-text contrast (#70) are merged. The next table
segments are gated empirical work, not reasons to manufacture additional features.
No locked-test run, real-data comparison or learning-effect report is
completed by this software-only progression.


## October 18 acquisition follow-up

Official archive acquisition is complete in #71; the previous sign-in/download
blocker is resolved. The prior table remains a historical plan. Current segmented
ownership before any real-data provenance/training change:

| Owner | Segment | Acceptance | Dependency |
|---|---|---|---|
| Platform engineer | Bounded archive inspector | Exact known shape, streaming CRC/hash receipt, resource/path checks, no row parsing or authorization claims | Private acquired archive; merged PR #72 |
| Model/data engineer | Organizer catalog mapping | One-to-one narrow assignment spelling crosswalk, exact release IDs/prompt/header tags, complete coverage and private outputs | Audited organizer sheet; merged #73, no chronology changes |
| Coordinator/data lead | Chronology evidence and clarification | Authoritative interpretation of mixed timezone labels and reviewed scoped ordering/exclusions | Public source ambiguity; organizer contact authorization pending |

The [catalog/chronology audit](catalog-chronology-audit.md) records source evidence
and remaining uncertainty. Real-source manifests, canonical histories and training
remain disabled. Data access no longer blocks structural/catalog setup; chronology
and source/provenance acceptance still block real model runs.

The prospective [comparative-study protocol](comparative-study.md) specifies
validation ranking, seed/failure policy and locked-test reporting before real
metrics exist. Its resource amendment and real-source evaluator remain pending;
it does not enable real training or replace any acceptance gate.

Reproducible structural diagnostics (#77), the pure label-free chronology
collector (#76) and its separate [CSV adapter](chronology-csv.md) (#79) are merged.
The adapter verifies declared restricted scope, hashes the exact private tables
and projects only the seven chronology fields. Independent review and private
replay preserved unresolved interpretation; no histories are created. Source-backed
chronology and reviewed real-source support remain the next import dependencies.

The day-nine [paired student bootstrap](student-bootstrap.md) (#80) is also merged
as a pure probability-score utility, without a test loader. Its original synthetic
checks and independent expanded-row oracle establish software arithmetic only;
real selection, calibration, locked-test evaluation and publication remain pending.

## October 18 HOME desktop continuation (local work, not rollout)

Owner: coordinating engineer. Purpose: verify the handover on this desktop and
record two dependency-ready, separately reviewed engineering segments.
Acceptance: isolated branches, synthetic local checks, independent review, draft
PRs, final-head CI and squash merges before calling either segment delivered.
Dependencies: repository write authentication for publication; private release and
authoritative chronology remain separate gates for empirical work.

| Owner | Segment | Acceptance | Dependency |
|---|---|---|---|
| Platform engineer | Bound DKT validation and checkpoint replay batches | Existing batch size bounds model calls; ordered outputs, unknown fallback and aggregate validation selection preserved | Existing DKT trainer/checkpoint; synthetic verification |
| Model engineer | Paired whole-student ranking intervals | ROC AUC and incorrect-positive AP; common cluster draws, ties, explicit one-class draw counts and conditional interval limits | Existing metric definitions/bootstrap; synthetic oracle |
| Coordinator | HOME verification and chronological record | Distinguish local work from merged delivery, record review/check evidence and remaining gates | Both engineering reviews; repository write authentication |

The corrected project directory was absent and was cloned without replacing any
checkout. Main is clean at `72725ca`; GitHub confirms PRs #75-81 merged and no open
PRs at inspection. CI, browser smoke and neural/encoder workflows succeeded on
that exact main head. The private release directory is absent on this desktop;
a clone does not transfer the archive, catalog, weights or private draft.
No redownload, organizer outreach, real import or real training was performed.

The current GitHub credential has read access but lacks repository push access.
Local implementation and independent review can proceed; PR publication, final-head
CI and merging require a writer account. These segments are not merged deliveries.
