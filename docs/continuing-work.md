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
| Coordinator | Integrated rollout record | Merged links, actual verification, corrected CI findings and explicit unmet gates | Merged #60-#66 behavior; no day-completion claim |
| Product engineer | Secondary-text contrast correction | Meaningful evidence/status/history/rank text meets 4.5:1 on actual normal/selected/hover surfaces; focused colors only | Scoped product audit; merged walkthrough #67 |
| Model engineer | Loaded-content inference profile | Bounded label-free queries/offline entries, exact identity hashes, separate load/cache/inference costs, restored CPU settings | Merged adapter #66; no encoder download or API activation |
| Coordinator/data lead | Real release receipt/audit | Nonempty valid archive, actual usage/catalog/grading/time verification | DataShop sign-in and working browser download |


Choice-to-attempt backend/UI (#56/#57), strict checkpoints (#55), cache preparation
(#58), optimizer/run (#59/#60), configured policy/backend UI (#61/#62), local
containers/CI (#63/#65) and loaded-content adapter (#66) are merged.
No locked-test run, real-data comparison or learning-effect report is
completed by this software-only progression.
