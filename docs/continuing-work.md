# Continuing sprint implementation

The user requests continuous progress across planned days. Complete and review small changes, integrate them, then advance to the next dependency-ready task. Day numbers organize reporting, not stopping points. Existing real-data access/terms and catalog verification gates remain open; synthetic smoke runs must never be presented as research evidence.

## Next segmented changes

| Owner | PR-sized change | Acceptance | Dependency |
|---|---|---|---|
| Data engineer | Explicit exercise/family holdout partition builder | Exercise families disjoint; no held-out target response in training or primary scored histories; splits independent of labels | Canonical interactions |
| Model engineer | Global and smoothed problem-rate baselines | Fit on training examples only; cold start/unknown fallback; deterministic JSON round trip | PredictionExample contract |
| Coordinator | Baseline artifact format + package registration | Strict versioned JSON; no pickle; reload parity; explicit synthetic/unverified provenance | Rate-model interface |
| Model engineer | Historical features and logistic regression | Counts/recent/concept features depend only on prior history; train-only preprocessing; saved parameters | Feature contract and research dependencies |
| Data engineer | Evaluation metrics and student summaries | Probability metrics/incorrect-positive PR-AUC defined; one-class metrics explicit; grouped summaries | Baseline prediction interface |
| Coordinator | Reproducible training/evaluation command and run manifests | Verify preprocessing hashes; tune/evaluate validation only by default; keep test untouched; record configs/seeds | Models, metrics, artifacts |

Other product, BKT, neural, calibration and release tasks follow in their own reviewed PRs once these foundations are integrated. Do not bundle multiple rows into a day-sized PR.

## Research interfaces for the next PRs

- Canonical `PredictionExample` contains prior first-attempt `history`, candidate metadata and a separate `label`.
- New research model modules live in `src/practice_engine/models/`; they never import demo API heuristics.
- Rate model: `RateBaseline.fit(examples, alpha=1.0)`, `predict(examples, per_problem=True) -> list[float]`, `to_dict() -> dict`, `from_dict(payload) -> RateBaseline`. Require nonempty train set and positive finite smoothing; unknown exercise falls back to global smoothed rate.
- Research artifacts wrap a JSON-serializable model payload with its model type/version and dataset/split/feature provenance. A saved model is not automatically the active API model.
- Holdout module lives under `data/` and returns partition metadata plus partitioned examples. Holdout histories exclude all validation/test exercise responses across all groups, including earlier held-out responses in later scored histories. Student holdouts keep observed test prefixes allowed under their separate protocol.
- Initial metrics live under `evaluation/`; accept examples and probabilities, and do not choose thresholds or calibrators using test data.
