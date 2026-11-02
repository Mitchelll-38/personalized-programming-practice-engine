# Day 1 integration contract

Local-only synthetic research demo; no trained model or Java execution. Python package `practice_engine` under `src/`. FastAPI app `api.main:app`. React/TypeScript Vite app under `web/`, proxy `/api` to localhost:8000 (strip prefix).

API responses:
- GET /health: {status: "ok"}
- GET /models/current: {model_id: "demo-history-v1", dataset_version: "synthetic-v1", is_demo: true, calibrated: false}
- GET /exercises: list of {problem_id, title, problem_text, concept_ids: string[], prerequisites: string[]}
- GET /students/demo/history: list of {student_id, problem_id, sequence_index: integer, correct: boolean, attempt_number: integer}
- GET /students/demo/profile: {student_id, is_demo: true, concepts: [{concept_id, estimated_performance: number, supporting_attempts: integer}]}
- GET /students/demo/recommendations: {student_id, is_demo: true, policy_version: "demo-ranking-v1", recommendations: [{problem_id, title, concept_ids, predicted_correctness: number, score: number, reasons: string[]}]}
- POST /predict body {history: [{problem_id, sequence_index, correct, attempt_number}], candidate_ids: string[]}; response {is_demo: true, predictions: [{problem_id, predicted_correctness}]}. Extra target response fields rejected.
- POST /attempts body {student_id: "demo", problem_id, correct: boolean}; response canonical stored interaction. Demo manual replay outcome only; server assigns sequence/attempt number. SQLite persistence, configurable PRACTICE_DB_PATH.

Seed original Java exercise descriptions and demo interactions directly in API package; no external data. Learner can inspect exercises and record a simulated correct/incorrect outcome; frontend must prominently explain that outcomes are simulated and predictions are uncalibrated demo estimates. API authors own demo heuristics and API tests; data engineer owns canonical research schemas/prefix/split logic. Their modules need not depend on one another on day 1.

November 2 demo prediction boundary — Owner: platform/API engineer. Purpose:
prevent a candidate's observed correctness from entering its own `/predict`
estimate. Dependency: the existing demo request schema and first-attempt
heuristic; no model training or replay persistence change. Acceptance: any
candidate ID that appears anywhere in supplied history returns HTTP 422 before
prediction. Distinct earlier exercise outcomes may still inform shared-concept
estimates, and multi-candidate order remains stable. Both true and false target
outcomes are covered by regression tests. The recommendation ranking may still
show previously attempted exercises for replay, under its separate policy.
The request validator now rejects overlap before invoking the heuristic. Focused
API/recommendation tests passed 73 cases, and the pinned full Python suite passed
1049 cases with four expected skips. These are synthetic software checks, not
measured predictive quality.

Day 2 additive profile diagnostics: `total_interactions` counts all stored outcomes,
`first_attempts` counts distinct exercises with an observed attempt numbered 1,
and `retries` counts interactions numbered above 1. Each concept additionally
includes `supporting_problem_ids` (distinct first-attempt exercises in sequence order)
and `evidence_status`: `no-history` for zero support, `limited-history` for one or
two exercises, `observed-first-attempt` for three or more. These labels describe
evidence volume, not statistical confidence or proven mastery. Zero support uses
the unchanged 0.5 neutral prior and must be displayed as having no personal evidence.
All evidence and outcomes remain synthetic; retries never alter concept estimates.
