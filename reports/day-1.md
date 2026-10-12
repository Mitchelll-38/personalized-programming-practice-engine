# Day 1 delivery — October 12, 2026

## Delivered

- Public GitHub repository created first, then API integration contract committed and pushed.
- Ten-day, three-engineer plan with daily responsibilities, dependencies, acceptance gates and scope cuts in `docs/sprint-plan.md`.
- Root agent: data contract, canonical validation, causal first-attempt examples, student-disjoint partitions, synthetic audit/CLI, dependency lock, README and CI.
- Backend agent: typed FastAPI demo, eight original Java exercises, SQLite persistence, transparent untrained prediction/ranking and API tests.
- Frontend agent: React/TypeScript replay dashboard, concept support counts, exercise inspection, recommendation reasons, simulated outcomes and connection recovery.

## Verification

- `python -m pytest -q`: **17 passed** (10 API, 7 data); one upstream Starlette TestClient/httpx deprecation warning.
- Synthetic CLI: 13 authored interactions, 6 synthetic students, 2 exercises; 12 primary first attempts and 1 retry excluded. Produced hashed audit/split manifests and nonempty train/validation/test files. These counts are fixture checks, not research findings.
- `npm run build`: TypeScript and Vite production build passed.
- Browser QA: offline API displayed connection error/retry; reconnect loaded the workspace. A simulated correct result increased history from 4 to 5 and updated concept estimates/ranking. Selecting another exercise and recording an incorrect result increased history to 6 and updated its concept estimate. Desktop and 390px mobile layouts inspected; [desktop screenshot](screenshots/day-1-desktop.jpg), [mobile screenshot](screenshots/day-1-mobile.jpg).
- Python package wheel build passed; `pip check` found no broken dependency requirements.
- CI definition runs tests, the fixture CLI and frontend build; remote run status is available in the repository Actions tab.

## Known boundaries

No real dataset acquired, release-specific importer implemented, models trained, calibrated probabilities produced or research metrics claimed. The official dataset link could not be read by the browsing tool because it redirected to sign-in; access, statement availability and redistribution terms remain a day-two dependency (see `docs/data-access.md`).

Research partitions currently cover held-out students only; exercise/family/joint protocols are planned for day 3. The application supports one local synthetic learner and manual replay outcomes. It has no authentication, Java runner or hosted deployment. Public student-code redistribution is not authorized by this work.

The demo predictor uses `(1 + correct first attempts) / (2 + first attempts)` per concept, then averages the candidate's concept values. Ranking prefers proximity to 0.65, penalizes weak prerequisites and previously attempted exercises. These are explicitly demo heuristics, not fitted baselines or the final prerequisite eligibility policy.
