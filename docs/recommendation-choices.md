# Recommendation choice events

Owner: coordinator (backend/API), product engineer (separate UI PR). Dependency:
merged generation PR #44 and snapshot storage #41. Purpose: retain explicit
exercise choices against the ranking that supplied them, separately from grades.
Acceptance: strict snapshot/problem request; existing, intact snapshot and ranked
candidate required; server assigns choice ID/time; preserve interactions and
snapshots; errors do not insert a choice; concurrent choices persist independently.

Contract: `POST /recommendation-choices` accepts only `snapshot_id` (32
lowercase hex) and `problem_id` (nonblank, up to 256 characters). Returns 201 with
`choice_id`, UTC `created_at`, `snapshot_id` and `problem_id`. Unknown snapshots
return 404; candidates absent from that snapshot return 422. Synthetic demo only;
no caller-supplied learner, outcome, timestamp or code. Old snapshot choices remain
valid and retain their original historical context. Repeated requests create
separate events, including retries after an ambiguous network failure; event
counts are not unique learner counts. UI must send only deliberate choices, not
automatic default selection. UI wiring and attempt linkage are separate PRs.

An additive `recommendation_choices` table preserves the generation record and
manual attempts. It has no public read endpoint or update/delete operation.
These events record a client's declared choice, not proof of exposure, execution,
recommendation causality or learning effectiveness. Local SQLite is not a
tamper-evident audit log. Keep databases in ignored private project storage.

Validation uses original synthetic requests and temporary private databases: context-bound persistence, old ranking preservation, concurrent inserts, strict fields, corrupt/unknown snapshot rejection and unchanged manual attempts. The database enforces a foreign key to the generation record on choice writes.
