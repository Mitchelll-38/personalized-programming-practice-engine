# Paired student bootstrap

Owner: coordinator/evaluation engineer. Purpose: implement the uncertainty unit
in the prospective comparative-study protocol without adding a test-data loader.
Acceptance: paired whole-student resampling with multiplicity, deterministic local
RNG, aggregate and equal-student log-loss/Brier intervals, explicit sparse-cluster
limits, fixed aggregate output and original synthetic boundary tests.
Dependencies: existing probability metric definitions; caller owns partitions,
source permission and any locked-test access. No model fitting/selection here.

Plan recorded October 18, 2026, before implementation: evaluate two aligned
prediction vectors once, retain student sufficient statistics privately, resample
the same clusters for both models, and report 95% percentile intervals for each
model and candidate-minus-reference differences. Independently review arithmetic,
cluster multiplicity and leakage boundaries before merging this standalone PR.

`practice_engine.evaluation.bootstrap.paired_student_bootstrap(examples, candidate,
reference, replicates=1000, seed=38)` accepts one nonempty list/tuple of prediction
examples and aligned probability vectors. It reuses the existing metric definitions
and validates both vectors. It uses a local RNG to sample N students with replacement
per replicate, where N is the observed student count. Every drawn cluster contributes
all its observations, retaining repeated draw multiplicity. Aggregate scores weight
observations; macro scores give each drawn student one equal contribution.

The fixed aggregate-only result reports point estimates, 95% intervals for each
model and paired candidate-minus-reference differences, counts, seed and method.
Lower log loss/Brier is better; negative differences favor the candidate. Intervals
use linear interpolation at the 2.5th/97.5th percentiles of replicate values.
Replicates must be integers in [100,10000], seed in [0,2**32-1]; runtime grows with
students times replicates. Fewer than two students yields estimates but null
intervals and an explicit reason. Few clusters can still give unstable intervals;
these are descriptive bootstrap estimates, not guarantees or significance claims.

No IDs, prompts, code or per-student statistics are returned; callers still own
publication review for aggregate results. No files, models, labels or RNG state
are changed. This utility has no source/partition certification, test loader,
ranking-metric intervals, selection logic or empirical result. It does not remove
the real-data chronology and provenance gates in the comparative-study protocol.
