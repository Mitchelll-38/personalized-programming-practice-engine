# Research engineering status

Execution report: October 18, 2026 (America/Toronto). Sprint days are work units;
this report aggregates reviewed changes across work units 3-10, not completed days of
empirical research. Earlier reports retain their original execution evidence.

| Work unit | Reviewed software delivery | Unmet integrated acceptance |
|---|---|---|
| 3: partitions/baselines | Family partitions/CLI (#9, #20, #25), rates/features/logistic (#10, #12, #15), portable artifacts/runs (#14, #17, #21, #29) | Real-data partitions and validation table |
| 4: BKT/evaluation | BKT (#16), probability/equal-student metrics (#13), portable inference/run integration (#21, #29, #30, #32) | Real-data comparison and latency measurements |
| 5: DKT | CPU environment, causal batching/forward, strict checkpoints and bounded trainer (#18, #19, #26, #31) | Real-data training, validation selection and measured run budget |
| 6: content inputs | Exact cache (#35), optional environment (#39), frozen local CodeBERT extraction (#45) | Verified real problem statements/concepts and content coverage |
| 7: content model/product | Causal batching/forward (#49, #53), checkpoint/cache/optimizer/run (#55, #58, #59, #60), loaded adapter (#66); ranking context (#41, #44) | Real-data training comparison and evidence-based model selection |
| 8: calibration/policy | Reliability/scalar (#24, #27), bound envelopes/run/API (#37, #38, #40), inspector (#36, #43), choices (#46, #48), linked outcomes (#56, #57), configured policy/disclosure (#61, #62) | Independent calibration evidence and policy effectiveness |
| 9: reproducibility/evaluation | Runtime-only containers (#63), real proxy/retry/recreation CI (#65), strict artifacts and offline content profiler (#68) | Selected-model locked-test report and grouped real-data errors |
| 10: release rehearsal | Locked image/runtime inputs, fresh Linux container rehearsal (#63, #65), synthetic walkthrough (#67), focused contrast correction (#70); evolving contracts/progress | Complete clean-machine research reproduction and final report/release |

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

On October 18, the official full S19 archive downloaded successfully through the
user-authenticated browser, passed ZIP verification and was privately extracted.
Its exact size/checksum and current research-only/non-redistribution observations
are recorded in [release acquisition](../docs/release-acquisition.md). Structural
audit found chronology/timezone issues requiring an explicit source-backed policy;
the organizer-linked catalog now has complete audited 50-problem coverage under
a narrow assignment spelling crosswalk, with one researcher's concept estimates.
[Chronology ambiguity](../docs/catalog-chronology-audit.md), reviewed mapping/use
policy, grading and real-source provenance remain import gates. There are no real-data prediction metrics, untouched-test report or
learning-effectiveness claims.

Next deliverables require the verified release/catalog, comparative real-data runs
and model selection. Locked-test comparison and final release work retain their own acceptance
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

HOME continuation, October 18: ranking uncertainty (#82) and bounded DKT
validation/reload (#83) passed independent review and all exact-final-head GitHub
checks before squash merge. They improve uncertainty arithmetic and validation
memory boundaries; they do not complete real comparison, resource approval or
locked-test acceptance. The private release/catalog/encoder weights acquired on
the earlier machine are absent in this desktop clone. No replacement dataset,
real import/training or organizer outreach was used. See the chronological ledger
for exact reviews, commits and local checks.

History-length summaries (#85) also passed independent exact-head review and all
applicable CI before squash merge. They provide fixed-bin aggregate arithmetic,
not a locked-test runner or empirical error report. The remaining real-source,
resource and selection dependencies above still apply.

Integrated code verification at `e4f4e84` passed 869 tests with three expected
skips on this desktop. This is synthetic software evidence; it does not satisfy
real-data comparison, calibration, locked-test or learning-effectiveness acceptance.
