# Coherent synthetic replay workspace

Owner: platform/API engineer. Purpose: keep the displayed history, concept profile,
and saved recommendation generation on one observed history version when another
client records an outcome during loading. Dependency: the existing demo history,
heuristic ranking, and recommendation snapshot storage contracts. The frontend
will consume this endpoint in a separate dependent change.

Acceptance: `GET /students/demo/workspace` returns the existing frontend snapshot
shape: `model`, `exercises`, `history`, `profile`, and `ranking`. One history read
supplies all three history-dependent fields. The ranking is recorded before the
response, with its candidate order, policy metadata, and history sequence position
matching the response. An outcome committed after that read may make the response
an earlier coherent view; the next request sees the new outcome. Existing endpoints
and synthetic/uncalibrated declarations retain their behavior.

Verification uses an isolated temporary SQLite database. An injected outcome
between the workspace history read and ranking storage must not change the
profile or ranking in that response. A later workspace request must include the
outcome. Existing endpoint regression tests must pass. This is a local synthetic
replay view, not an authenticated learner session or a research result.
