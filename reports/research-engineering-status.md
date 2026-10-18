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
| 7: content model/product | Causal content batching/forward (#49, #53), strict checkpoint/cache/optimizer (#55, #58, #59); generated ranking context (#41, #44) | Reviewed run publication and real-data training comparison |
| 8: calibration/policy | Reliability diagnostics/scalar (#24, #27), bound envelopes/run/API (#37, #38, #40), inspector (#36, #43), explicit choices (#46, #48), linked outcomes (#56, #57), configured policy (#61) | Independent calibration evidence and policy effectiveness |

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

Next deliverables are separate content-run publication, optional policy disclosure
and local container PRs. Locked-test comparison, packaging and release work retain their own acceptance
gates. A green synthetic test suite does not complete
those gates. Hosted deployment remains a separate milestone.


A local timing smoke on October 17 used the original committed synthetic fixture,
seed 38, a problem-rate artifact (8 train/2 validation examples) and two label-free
validation queries. Test bytes were integrity-checked by the training workflow;
no test examples were parsed or evaluated. On Windows/Python 3.12.5, Intel Core
Ultra 7 155U (12 cores/14 logical processors), 100 repeated loaded-adapter calls
after five warmups measured 0.0802 ms median and 0.0953 ms nearest-rank p95 per
two-query batch. Read/parse/validation measured 17.4015 ms separately; it is not a
guaranteed cold-disk timing. The machine was also running development tasks.
This tiny repeated synthetic batch is a software smoke, not production performance,
model accuracy or an encoder/API benchmark. Exact bytes/config and aggregate report
remain under ignored `artifacts/inference-profile-smoke/`; see the
[inference timing contract](../docs/inference-profile.md).
