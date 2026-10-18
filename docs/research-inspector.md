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
Responses are checked against the requested candidate and require literal boolean
declarations: `is_synthetic=true`, a boolean `calibrated`, `research_results=false`,
with `source_kind=synthetic`. Missing flags and string booleans fail inspection.
The prediction response supplies the displayed model metadata, so a
model replaced between metadata and prediction requests is identified correctly.
No configured research artifact produces a quiet empty state; other failures have
a separate **Retry inspection** action and do not break replay snapshot loading.

Playwright uses isolated synthetic route fixtures to check request timing, exclusion
of retries/target responses, catalog metadata, history refresh, missing configuration,
recoverable errors, pending-request cancellation and already-attempted candidates.
These mocked probabilities test UI behavior; they are not measured model results.

## Temperature-scaled synthetic output

Owner: baseline engineer. Purpose: display the calibrated research API introduced
in PR #40 without claiming measured reliability. Acceptance: preserve uncalibrated
flow and strict flags, reject malformed calibrated declarations, identify scalar
application and its validation fitting record. No backend or policy selection is
changed by this UI follow-up.

`calibrated=true` is accepted only for the known temperature envelope/method with
a finite positive scalar in the declared fitting grid. The validation receipt must
identify validation fitting, a positive integer example count, valid hash strings
and source/split provenance matching the displayed model. These client checks
protect presentation; the backend owns artifact/payload validation. The client
does not recompute hashes or authenticate the producer.

The panel shows **Temperature-scaled synthetic estimate**, the scalar and fitting
count, followed by **reliability has not been independently established**. An
optional record discloses method and envelope/base/fitting hashes. Same-validation
fitting is not independent calibration evidence. The existing uncalibrated label,
request timing/cancellation, error recovery and heuristic replay remain unchanged.
Browser fixtures check valid mobile presentation and malformed metadata rejection;
their displayed probabilities remain synthetic UI test data.
