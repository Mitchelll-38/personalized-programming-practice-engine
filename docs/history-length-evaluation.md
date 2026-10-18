# History-length evaluation

Owner: model engineer. Purpose: implement the comparative-study report's fixed
history-length strata without introducing a data loader or unlocking test data.
Acceptance: bins 0, 1-4, 5-19 and 20+ use the number of permitted prior interactions;
validate all aligned input before grouping; preserve existing aggregate metric
semantics; report explicit empty bins; return no IDs or rows. Original synthetic
tests cover boundaries, class sparsity, invalid inputs and count conservation.
Dependencies: existing prediction-example schema and evaluation metrics. Source
permission, causal history construction, frozen selection and locked-test access
remain caller responsibilities. No real import, fitting or file access is added.

Plan recorded before implementation: validate examples and shape/probability
boundaries, compute each fixed bin using the existing evaluator, and expose only
aggregate summaries. Independently review the final commit before publication.

`evaluate_history_lengths(examples, probabilities)` returns four fixed `strata`
keys and overall example/student counts. Nonempty summaries match `evaluate`'s
aggregate metrics exactly, including fixed loss clipping, tied ranking scores and
null one-class ranking metrics. Empty bins have zero counts, null scores and
prevalence, and `empty_stratum` reasons. Student counts within bins overlap and
must not be summed to obtain the overall distinct-student count. Equal-student
macro metrics are omitted; this interface describes observation-weighted strata.
Input examples must be nonempty validated prediction examples; copied malformed
models and invalid aligned probability vectors are rejected before grouping.
The utility does not establish that supplied histories are causal or permitted.
No student IDs, prompts, code, probabilities or per-student scores are returned.
Synthetic checks establish arithmetic and boundaries only, not research results.
