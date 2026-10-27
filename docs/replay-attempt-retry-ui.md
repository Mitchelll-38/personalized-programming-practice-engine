# Synthetic replay retry behavior

Owner: product frontend engineer. Purpose: avoid duplicate demo interactions
when an attempt response is lost after the server commits. Dependency: backend
request receipts in `fix/replay-idempotency-api` (`d045dc6`); this is a separate
client segment and does not change the research predictor.

Acceptance: each clicked simulation intent sends a fresh lowercase 32-hex
`request_id`. If the response is ambiguous, repeating the same exercise and
outcome sends the exact same problem, correctness, optional acknowledged
`choice_id` and request ID, even after selecting another exercise or refreshing
the workspace. A different exercise or outcome is a new explicit intent with a
new ID. A confirmed response clears the pending intent before workspace refresh;
failed refresh keeps the existing save guard. A choice acknowledged after an
unlinked submission never attaches retroactively to that retry. Browser checks
cover lost responses, exact retries, new intents and choice linkage. HTTP 404,
409 and 422 definitively reject the submitted intent: the client clears that
request and its choice link, explains the rejection, and sends nothing else
until the learner explicitly clicks a simulation button again. Network and 5xx
failures retain the original request for exact retry.
