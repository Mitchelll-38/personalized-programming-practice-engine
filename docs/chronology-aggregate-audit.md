# Aggregate chronology observations

Owner: model/data engineer. Purpose: make the private chronology observations
reproducible without selecting a timezone interpretation or creating histories.
Dependency: the existing source-evidence contract; no CSV integration dependency.
Acceptance: immutable projected input, fixed aggregate output, strict parsers,
permutation invariance, scoped Order only, synthetic boundary tests and independent
review. Implementation follows this recorded plan in one isolated PR.

`audit_chronology(events)` accepts frozen `ChronologyEvent` projections containing
only exact subject/assignment/problem IDs, event type, timestamp, timezone and
Order strings. It performs no I/O and accepts no labels, code or target responses.
The caller owns source hashing, bounded CSV projection and metadata verification.
The declared diagnostic scope is always subject/assignment/problem.

Outputs are detached fixed-key aggregates for all events and `Run.Program` events
(not score-validated submissions). Raw timezone literals are classified as `UTC`,
`0`, missing or other; unknown input values never become output keys. Timestamps
require ISO dates and seconds, at most six fractional digits and optional ISO
offset/Z. Aware timestamps are counted but excluded from wall-time diagnostics;
invalid timestamp/Order strings are counted, never silently coerced.

Tie counts concern naive wall-time equality, not simultaneous instants. Order is
ASCII nonnegative decimal without leading zeros. Duplicate Order groups prevent
comparisons across either adjacent boundary; CSV order never resolves duplicates.
Adjacent uniquely ordered naive events yield raw wall-time decreases. Separate
counts distinguish same-nonempty-literal comparable pairs/decreases from mixed or
missing-literal incomparable pairs. Even same-literal observations are not proof
that the source convention is correct. No timezone arithmetic is performed.

The report always states unresolved interpretation, no normalization and no
verified global timeline. It contains no IDs, event values, per-subject outputs,
histories or authorization/provenance flags. It does not select exclusions or
interpretation, and does not enable real-data import or training.
