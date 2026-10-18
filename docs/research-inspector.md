# Optional fitted baseline inspection

Owner: baseline engineer. Purpose: inspect the stateless synthetic research API
without selecting it for replay. Acceptance: explicit opt-in, label-free causal
queries, distinct new candidates, stale-request cancellation and independently
recoverable empty/error states. Dependency: merged research API PR #32.

Select an exercise, then choose **Inspect fitted baseline** below its explanation.
The panel identifies the fitted synthetic model, model version and dataset version,
and labels the prediction uncalibrated software-test output. The existing ranking,
concept profile, simulated outcomes and footer continue describing the heuristic.
No trained model is selected for recommendations and no learning gain is claimed.

Requests join statement/concept metadata from the loaded exercise catalog onto
sorted first-attempt history only. The next sequence position follows **all**
recorded interactions, including retries. The candidate includes only ID, statement
and concepts. Historical outcomes are permitted; target labels and candidate code
are absent. Missing catalog metadata fails inspection rather than fabricating it.
An exercise appearing anywhere in history cannot receive a first-attempt prediction;
the panel explains this while keeping simulated demo retries available.

Selection/history changes reset opt-in and abort pending requests. Hiding the panel
or refreshing/saving the replay also aborts work and hides previous probabilities.
Responses are checked against the requested candidate and synthetic/uncalibrated
declarations. The prediction response supplies the displayed model metadata, so a
model replaced between metadata and prediction requests is identified correctly.
No configured research artifact produces a quiet empty state; other failures have
a separate **Retry inspection** action and do not break replay snapshot loading.

Playwright uses isolated synthetic route fixtures to check request timing, exclusion
of retries/target responses, catalog metadata, history refresh, missing configuration,
recoverable errors, pending-request cancellation and already-attempted candidates.
These mocked probabilities test UI behavior; they are not measured model results.
