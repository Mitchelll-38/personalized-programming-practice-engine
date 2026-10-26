# Synthetic replay attempt receipts

Owner: product/platform backend engineer. Purpose: prevent a simulated outcome
from being appended twice when its first HTTP response is lost and the client
retries. This is a separate backend segment from the client retry workflow.
Dependencies: existing SQLite replay and optional choice-to-attempt linkage;
no real-source data or trained model is involved.

Acceptance: `POST /attempts` accepts an optional strict lowercase 32-hex
`request_id`. The first valid submission appends one interaction and stores its
receipt atomically. Repeating the same ID with the same student, problem,
correctness and optional choice ID returns that interaction without appending
another. Reusing the ID with different values returns HTTP 409. Concurrent
identical submissions converge on one interaction. Existing callers that omit
`request_id` retain current behavior, including choice-linked retries. Invalid
IDs return HTTP 422. Receipts contain synthetic replay identifiers only.
