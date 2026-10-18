# Latest workspace request owns visible state

Owner: baseline engineer. Purpose: prevent an older workspace request replacing
newer data or clearing its loading/error state. Dependency: existing snapshot API
and React StrictMode. Acceptance: latest-request-wins for success, failure and
completion, with deterministic delayed-response browser checks. No choice UI or
backend change is included.

StrictMode replays the initial effect, so two snapshot batches can overlap. A late
first batch previously replaced the snapshot object after inspection was enabled,
causing duplicate prediction requests; a stale failure could also publish an error
or clear loading while a newer request remained pending.

Each `App.load` now captures a monotonically increasing generation. Only the
current generation publishes snapshot/selection, clears refresh-pending, reports
errors or finishes loading. Effect cleanup invalidates outstanding generations.
Requests already in flight may still finish or create server generation records;
the guard controls visible state rather than promising network cancellation.

Browser regressions hold the two initial batches independently, finish them in
opposite orders and verify stale success/failure cannot replace current data,
retrigger inspection or expose an incorrect ready state. Latest failures still
produce the existing recoverable connection error. No assertion count is relaxed.
