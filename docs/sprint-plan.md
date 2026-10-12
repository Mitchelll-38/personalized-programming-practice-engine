# Two-week engineering plan

**Sprint:** October 12–23, 2026 · 10 working days · three engineers.

Build a reproducible Java knowledge-tracing MVP with an inspectable replay application. The attached brief is a design input, not a claim that its proposed models or results already exist. It estimated 6–10 weeks part-time; this sprint assumes three people working roughly full-time (30 engineer-days). Access to approved data and one suitable GPU are dependencies. Two weeks can produce a narrow research/product MVP; extensive ablations, credible learning-effectiveness studies, and transformer extensions remain later work.

## Roles and working agreement

| Engineer | Ownership | Review responsibility |
|---|---|---|
| A — data/ML lead | Task definition, canonical data, splits, baselines, training and evaluation | Review prediction timing and backend inference |
| B — backend/ML platform | API, persistence, artifacts, model integration, reproducibility and CI | Review data contracts and frontend API use |
| C — product/frontend | Learner dashboard, replay flow, explanations, accessibility, product QA | Review observable behavior and documentation |

Day 1 is executed by the root agent (A), `api_engineer` (B), and `frontend_engineer` (C). Shared API contract freezes before parallel implementation; each owns separate files. Subsequent team workflow: 15-minute daily standup, small reviewed PRs, cross-owner review, and a daily runnable integration demo. Reserve approximately one hour per person daily for review/integration; day 10 is a release buffer. Fix leakage or broken integration before adding model complexity.

The user's required workflow is codified in [AGENTS.md](../AGENTS.md): isolated worktrees, one coherent change per small PR, independent agent review, final-head CI, and ordered squash merges. This applies to features, fixes, tests, documentation and CI. Daily delivery reports must link the individual PRs; a sprint day is not a single bundled PR.

## Backlog and day-by-day delivery

Each row is roughly one day's work per engineer. Acceptance criteria are a gate for the integrated team, not simply a list of files.

| Day/date | A — data and modeling | B — platform and API | C — product | Integrated acceptance / dependency |
|---|---|---|---|---|
| **1 · Mon Oct 12** | Strict canonical schema; first-attempt causal prefixes; reproducible student partitions; synthetic fixture/audit CLI; dataset access log | Typed FastAPI endpoints; synthetic demo predictor; SQLite attempts; endpoint/persistence tests | React/TS dashboard; inspect recommendations/exercises; record simulated outcomes; loading/error/mobile states | Public repo created first; clean setup; leakage tests and web build pass; replay updates stored history and recommendations; all estimates labeled synthetic/untrained |
| **2 · Tue Oct 13** | Obtain approved release; audit keys, grading, timestamps, duplicate events, missing text/tags; implement release-specific importer | Version dataset/feature/model manifests; importer CLI integration; validate canonical API/research boundaries | Improve diagnostics, cold start, supporting-history display; API smoke test automation | Signed-off data provenance and label definition. If access unavailable, continue with fixtures and mark all empirical work blocked; no real-data results |
| **3 · Wed Oct 14** | Lock held-out-student + exercise/family partitions; global/problem-rate and logistic baselines; train-only features | Artifact format + reload consistency; run registry with config/seed/hash; batch prediction adapter | Catalog, replay selection, recommendation reason details; unknown/empty-state behavior | Train/validation/test disjoint; no held-out labels in fitted features; baseline evaluation on validation only |
| **4 · Thu Oct 15** | BKT fitting; student-weighted summaries; cold-start comparisons | BKT serving adapter; offline evaluate command; CLI/API parity and latency measurement | Concept profile with evidence counts and explanation boundaries | Global/problem-rate, logistic, BKT validation table reproducible; demo and trained artifacts visibly differentiated |
| **5 · Fri Oct 16** | LSTM DKT; sequence masks; training/validation loop and early stopping | Batch padding, checkpoint/version loading; test future invariance and masked loss | End-to-end replay with selected baseline; responsive/a11y pass | DKT smoke run + causality/padding checks; week-one demo. GPU/run cost measured before scaling |
| **6 · Mon Oct 19** | Frozen CodeBERT embeddings for allowed text/historical code; vocabulary fit on training only | Hash/version embedding cache; candidate unknown-ID handling; content artifact adapter | Estimated concept performance from fixed probes; short-history caveats | Reusable embeddings with encoder revision/truncation manifest; target code absent; requires verified problem text |
| **7 · Tue Oct 20** | Content-aware LSTM; same splits/budget as DKT; tune on validation | Integrate selected candidate and failure fallback; batch/latency checks | Prerequisite and novelty explanations; recommendation event capture UI | Content run reproducible; compare with baselines fairly; adopt only if evidence supports it |
| **8 · Wed Oct 21** | Validation-only calibration; core ablations (text/code/concepts); multiple seeds if budget allows | Version calibration + policy; candidate/policy/attempt log; SQLite migrations | Model metadata and confidence presentation; review explanation accuracy | Calibrator never sees test; policy challenge range configurable; predictions separated from learning claims |
| **9 · Thu Oct 22** | Run once on locked tests; ROC-AUC, incorrect-class PR-AUC, log loss, Brier; grouped uncertainty/error analysis | Docker/local deployment recipe; artifact integrity; API regression and reproducibility check | Research results view/report links; usability walkthrough; fix release defects | Untouched test report with actual counts and limitations; documented missing runs. No selecting model using test metrics |
| **10 · Fri Oct 23** | Research report, reproduction audit and honest resume-ready results | Clean-machine rehearsal, CI green, versioned release and rollback instructions | Cross-device QA, screenshots/demo guide, README polish | One-command documented reproduction; replay demo; actual results/provenance; remaining backlog explicitly listed |

## Critical path and decision gates

1. Approved dataset + grading semantics → importer → locked splits → baselines → DKT → content model → calibration → locked-test report.
2. The product runs on synthetic fixtures in parallel; the interface must never disguise fixture output as measured results.
3. **End of day 2:** if access/terms or statement text remain unresolved, keep building import/serving interfaces, but defer real-data training and report the dependency. No substitute scraped student code.
4. **End of day 5:** if DKT is unstable or compute unavailable, ship logistic/BKT inference first and move neural experiments to the follow-up sprint.
5. **End of day 7:** select on validation evidence. A simpler winning model is an acceptable outcome. If content isn't accessible, leave that research question unanswered.
6. **Day 9:** run locked tests after model selection. For exercise holdouts, prevent held-out target responses entering scored primary histories, group near-duplicate exercise families, and map held-out IDs to unknown.

## Definition of done

- Source changes reviewed and CI green; a new developer can reproduce the demo and documented runs.
- Data release, permission/terms, label definition, order/tie rule, exclusions, counts, hashes, seed and partitions recorded.
- Prediction contract: candidate text/tags plus strictly previous observed interactions; no candidate code, outcome or later interactions.
- Research artifacts identify encoder/config/data/split/calibration versions. Test partitions stay untouched during tuning.
- Dashboard calls outputs **estimated performance**, states history support, distinguishes cold start and uncalibrated synthetic output.
- Completed attempts persist; retries do not inflate primary first-attempt evidence; errors are visible and recoverable.
- Measured predictive quality and policy behavior are reported separately; no assertion of improved learning from offline prediction scores.

## Scope cuts and follow-up

Defer causal transformer, generated/clustering concepts, encoder fine-tuning, second language/dataset, prospective recommendation study, authentication/multi-user hosting and sandboxed Java execution. The day-one API is a local research replay demo with trusted simulated grading; it must not be exposed as a public grading service. A public source repo is the day-one publication deliverable; hosted application deployment is a separate milestone.

## Day 1 review checklist

Execution progress: [day-two report](../reports/day-2.md) records the segmented PR rollout and the still-unmet real-data access/metadata acceptance gates. Engineering completion must not be interpreted as signed-off empirical data provenance.

- [x] Public GitHub repo initialized and first contract pushed before implementation.
- [x] Separate implementation lanes dispatched to backend and frontend agents.
- [x] Canonical data schema, causal prefixes, first-attempt filtering and deterministic student split implemented.
- [x] Dataset access investigation recorded; real release and terms still unverified.
- [x] Integration tests and web build completed (see day-one report for final evidence).
- [x] End-to-end replay verified; final source prepared for publication (see day-one report).
