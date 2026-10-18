# Explicit recommendation choices in the replay

Owner: baseline engineer. Purpose: record deliberate recommendation choices
separately from inspecting prompts and recording simulated correctness.
Dependencies: generated ranking snapshots (PR #44) and the separate backend choice
endpoint. Acceptance: explicit-only POST, exact snapshot/candidate binding, private
recoverable errors, no automatic retry and no stale acknowledgement across contexts.

Default selection, ranking-card clicks and library changes only inspect exercises.
**Choose this recommendation** is a separate action on the selected recommendation.
It submits only `{snapshot_id, problem_id}` from the displayed ranking to
`POST /recommendation-choices`. A valid 201 acknowledgement must contain a server
choice ID, UTC timestamp and the exact submitted snapshot/problem. It contains no
correctness, submitted code or attempt linkage. Choosing does not grade an exercise
or establish recommendation effectiveness, exposure or learning gain.

The button disables during its request/replay refresh and after acknowledgement.
Manual replay remains available even while a choice request fails or is pending.
Selection or ranking-snapshot changes reset the choice state, abort pending client
work and prevent old acknowledgements from appearing on a new context. An aborted
or network-failed request might already have committed on the server. There is no
automatic retry; visible errors explain that manual retry may create another event.
Repeated explicit submissions are separate events; no idempotency is promised.

The backend contract is [recommendation-choices.md](recommendation-choices.md).
Unknown snapshots return 404 and candidates absent from that snapshot return 422;
an older snapshot remains valid historical context. The UI does not replace a
failed snapshot ID with a newly generated ID silently. Fetching fresh ranking data
does not itself log a choice. The research inspector and heuristic ranking/profile
continue operating independently of this action.

The unmocked live browser case captures the displayed generation's actual response
identity, submits one explicit choice and checks the persisted 201 acknowledgement.
History/profile stay identical and no attempt request is sent. Separate mocked
browser cases cover failure/retry, duplicate activation and stale-context handling.
