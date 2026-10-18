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

## Ranking uncertainty segment — October 18, 2026

Owner: model engineer. Purpose: complete the prospective study's aggregate
ROC-AUC and incorrect-positive average-precision uncertainty arithmetic.
Acceptance: paired whole-student draws with full multiplicity, existing tie and
class definitions, deterministic RNG, explicit undefined replicate counts,
aggregate-only output and original synthetic expanded-row oracle tests.
Dependencies: existing evaluation metrics and percentile method; caller owns data,
partition and resource approval. No loader, fitting, selection or import changes.
Plan recorded before implementation: add a separate ranking-only API, reuse the
existing ranking definitions, and independently review one-class and sparse cases.

`practice_engine.evaluation.ranking_bootstrap.paired_student_ranking_bootstrap`
accepts the same examples, two aligned p(correct) vectors, seed and replicate
bounds as the probability bootstrap. It reports aggregate correct-positive ROC
AUC and incorrect-positive step AP, with ties grouped by the existing evaluator.
It deliberately does not average student ranking scores. Positive paired
candidate-minus-reference differences favor the candidate (unlike loss scores).

Each requested draw samples N whole students with replacement, expands every
selected student's rows with multiplicity and uses the same rows for both models.
A draw containing only one label is undefined for both metrics; it is counted
and skipped without replacement draws. Reports include requested/attempted/valid/
undefined replicate counts. Percentile intervals are conditional on draws with
both labels, and may be misleading when many draws are undefined or few clusters
exist. They do not establish nominal population coverage or significance.
Fewer than two valid replicates suppresses intervals. One-class input also yields
null point estimates; fewer than two students yields no attempted draws or
intervals, even when its point estimates are defined.

The original probability bootstrap schema is unchanged. Ranking runtime grows
with replicates times expanded observations and sorting cost, with expanded rows
held only for one draw. A caller must budget real evaluations before running;
this implementation does not establish full-release performance. Outputs contain
no student IDs or rows. Original synthetic tests establish software arithmetic
only; real evaluation, publication rights and all chronology gates remain pending.
