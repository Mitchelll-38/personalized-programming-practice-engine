# Linking a recorded choice to a simulated outcome

Owner: coordinator (storage/API); product engineer owns a separate UI change.
Purpose: bind an explicit recommendation choice to its later manual outcome without
conflating selection and correctness. Dependencies: choice backend #46 and existing
attempt transactions. Acceptance: optional strict choice_id; matching existing
choice required; interaction and link in one transaction; identical retries return
the original interaction; conflicting outcomes fail; ordinary unlinked replay
retains its existing behavior. No retroactive or inferred choice association.

The API accepts an optional `choice_id` to `POST /attempts`, retaining its current response
shape/status201. A valid choice must match the supplied problem. Unknown choices
return404; a different known exercise returns422. Unknown catalog exercises retain
the existing404 response before link validation. An already-linked choice with different
correctness409. Repeating the identical choice/problem/correct request returns the
original interaction and appends no retry. This is explicit per-choice idempotency,
not global idempotency for unlinked manual attempts. Each choice links to at most
one interaction; a later deliberate retry can use a new choice or remain unlinked.

An additive SQLite link table references both choice and interaction keys. The
same immediate transaction validates context, allocates attempt/sequence numbers,
inserts the interaction and inserts its link. A failed link rolls back the new
attempt too. A choice action alone never supplies correctness or creates an
attempt. These synthetic audit links do not prove grading accuracy, causal policy
benefit or learning effectiveness. Keep databases and event rows out of public Git.


Tests use original synthetic choices/outcomes and temporary databases. They check
persisted links, identical retries after later attempts, conflicting/out-of-context
failures, eight simultaneous retries, unchanged unlinked retry behavior, and a
forced link-insert failure that rolls back interaction numbering and content.
