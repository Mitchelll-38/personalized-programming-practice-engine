# Calibration diagnostics

`practice_engine.evaluation.reliability.reliability_summary(examples, probabilities)`
describes how predicted **p(correct)** compares with observed correctness. It does
not fit a calibrator, select a model or access files. The caller must supply the
intended partition; tuning remains validation-only and locked tests stay untouched.

The default uses ten fixed equal-width bins and equal interaction weights.
`n_bins` accepts integers from 1 to 100. Each bin includes its lower endpoint and
excludes its upper endpoint, except the final bin includes probability 1.
Empty bins have zero weight/counts and null means/frequencies/gaps. Both single-class
and exact 0/1 probabilities are supported without clipping.

`weighting="student"` gives each student equal total weight, divided equally among
their observations. These weights are computed across the full supplied partition,
then retained inside bins. This differs from independently reweighting students
within each bin and prevents long histories dominating the overall diagnostic.
Counts remain raw observation/student counts; `weight_mass` identifies the actual
bin contribution.

Expected calibration error (ECE) sums each bin's weight mass times the absolute
difference between weighted mean probability and weighted observed correctness.
It is a descriptive, bin-dependent finite-sample statistic. A low ECE does not
certify individual confidence, concept mastery or learning effectiveness. No
confidence interval is produced; small bins should be interpreted using their
counts. Bin edges/weighting should be fixed before comparing experiments.

The implementation has only been checked on original synthetic observations.
No real-data calibration result is claimed, and this PR does not change API model
selection, the uncalibrated artifact flag or dashboard behavior.

## Evaluation input validation fix

Owner: data/ML engineer. Purpose: reject copied or otherwise malformed
`PredictionExample` rows before probability metrics or calibration diagnostics
can report impossible correctness rates. Acceptance: both `evaluate` and
`reliability_summary` reject invalid row types, non-Boolean labels, blank student
IDs and invalid nested history; valid synthetic reports retain their existing
values. Dependency: the existing canonical schema only; no private data, source
import or locked-test access is needed.
