# Research engineering status

Execution report: October 17, 2026 (America/Toronto). Sprint days are work units;
this report aggregates reviewed changes across days 3-8, not six completed days of
empirical research. Earlier reports retain their original execution evidence.

| Work unit | Reviewed software delivery | Unmet integrated acceptance |
|---|---|---|
| 3: partitions/baselines | Family partitions/CLI (#9, #20, #25), rates/features/logistic (#10, #12, #15), portable artifacts/runs (#14, #17, #21, #29) | Real-data partitions and validation table |
| 4: BKT/evaluation | BKT (#16), probability/equal-student metrics (#13), portable inference/run integration (#21, #29, #30, #32) | Real-data comparison and latency measurements |
| 5: DKT | CPU environment, causal batching/forward, strict checkpoints and bounded trainer (#18, #19, #26, #31) | Real-data training, validation selection and measured run budget |
| 6: content inputs | Exact cache (#35), optional environment (#39), frozen local CodeBERT extraction (#45) | Verified real problem statements/concepts and content coverage |
| 7: content model/product | Separate content batching/forward changes planned; generated ranking context now retained (#41, #44) | Content model/training comparison and explicit choice UI |
| 8: calibration/policy | Reliability diagnostics/scalar (#24, #27), bound envelopes/run/API (#37, #38, #40), inspector (#36, #43) | Independent calibration evidence, actual choice/attempt linkage and policy effectiveness |

PR numbers refer to the [public repository PR history](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pulls?q=is%3Apr+is%3Amerged).
Detailed review findings, test evidence and direct feature links are maintained in
[progress.md](../docs/progress.md) and each PR description. Each behavior shipped
through its own PR; reporting groups do not combine their implementation diffs.

The local replay remains a synthetic heuristic. The optional stateless research
inspector can display fitted synthetic baselines and temperature-scaled outputs;
configuring it does not select a new replay policy. Same-validation calibration
diagnostics are fitting diagnostics, not independent reliability evidence.

Frozen CodeBERT now executes locally using privately downloaded, checksum-verified
weights. A separate smoke encoded three original synthetic content inputs to
finite 768-dimensional vectors and reproduced cache hits. This establishes an
encoder runtime and cache behavior only. No student content was used or sent to a
remote inference service. Weights/cache/receipt remain outside public Git under
ignored project storage. Checkpoint-specific licensing metadata is still absent;
source-code MIT observations are recorded separately in the encoder contract.

No usable CodeWorkout release has been obtained. Earlier downloads are empty and
the current browser session needs manual sign-in. The release, usage permissions,
statement/concept catalog, first-scored-run grading interpretation and timestamps
must be verified before real import/training. There are no measured real-data
metrics, untouched-test report or learning-effectiveness claims.

Next deliverables are separate choice backend/UI PRs and content batching/forward
PRs. Later training/checkpoint, locked-test comparison, packaging and release work
retain their own acceptance gates. A green synthetic test suite does not complete
those gates. Hosted deployment remains a separate milestone.
