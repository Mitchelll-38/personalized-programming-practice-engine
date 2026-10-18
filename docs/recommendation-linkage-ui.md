# Optional choice-to-simulated-outcome linkage

Owner: baseline engineer. Purpose: attach a previously acknowledged deliberate
choice to the next explicitly simulated outcome in the same displayed context.
Dependencies: choice UI #48 and the separate optional-linkage backend PR.
Acceptance: capture a matching acknowledged choice at click time only, preserve
pending/unlinked simulation, reset context/success, retain ambiguous failures for
explicit retry, and surface link errors without automatic fallback.

Choosing still never submits correctness. Once a valid choice acknowledgement
matches the displayed snapshot/problem, a note explains that the next simulated
outcome will link to it. Clicking a simulation button adds optional `choice_id` to
the existing `/attempts` body. Without an acknowledgement, including while choice
storage is pending, the original unlinked body is sent. A later acknowledgement
does not retroactively attach to an already submitted outcome.

Selection/snapshot changes and acknowledged outcome success clear the local link.
If the outcome request fails ambiguously, the same choice remains available for
an explicit retry. The backend returns the original interaction for an identical
choice/problem/correct retry; the UI refreshes from that unchanged receipt rather
than appending an optimistic interaction. No new choice is created for retry.
Conflicting-outcome 409, missing-choice 404 and wrong-problem 422 have explicit
errors. The UI never silently drops the choice ID or retries unlinked. If saving
succeeded but workspace refresh failed, existing refresh-pending behavior blocks
another simulation until refresh recovery.

The [backend linkage contract](choice-attempt-links.md) owns atomic persistence and
duplicate-safe receipts. These records remain synthetic replay events, not proof
of exposure, recommendation causality or learning effectiveness. No research model
or ranking policy changes. Browser fixtures exercise request/context/retry behavior
independently of the backend's transaction tests.
