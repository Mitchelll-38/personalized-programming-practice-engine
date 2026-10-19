# Project progress record

Maintained during implementation. Dates use the client's America/Toronto context;
sprint day numbers are planning units. PR descriptions carry detailed scope,
tests, limitations and review evidence. Entries below describe merged software,
not measured learning effectiveness or real-data research results.

## October 12, 2026 — setup and replay foundations

The public repository was created before implementation. Day-one source established
the canonical task, causal first-attempt pipeline, synthetic API/SQLite replay and
React dashboard. Later work switched fully to isolated agent branches and small,
independently reviewed PRs. See [day-one report](../reports/day-1.md).

| Merged PR | Progress / decision |
|---|---|
| [#1](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/1) | Repository-wide small-PR/worktree/review rules and PR template |
| [#3](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/3) | Processing version manifests and output-integrity hashes |
| [#2](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/2) | Explicit first-attempt/retry denominators and no-personal-evidence concept labels |
| [#4](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/4) | Strict organizer-format importer; review caught duplicate CSV headers, fixed before merge |
| [#5](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/5) | Importer connected to audited canonical preprocessing CLI |
| [#6](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/6) | Live Chromium replay/persistence test; direct Vite launch fixed Windows shutdown |
| [#7](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/7) | Day-two delivery, verification and data-access gates recorded |

## October 12, 2026 — continued research engineering

The user instructed continued work across day boundaries and multiple focused PRs
within each day. Data/ML/platform engineers continued in separate worktrees and
cross-reviewed changes. This work implements the software behind later planned
days; the empirical dataset gate is tracked separately.

| Merged PR | Progress / decision |
|---|---|
| [#8](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/8) | Continuous work policy and dependency-ready implementation contracts |
| [#9](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/9) | Explicit family-disjoint holdouts; held-out exercise responses excluded from all scored histories |
| [#10](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/10) | Train-only global/problem success-rate models, strict JSON and unknown fallback |
| [#11](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/11) | Optional research dependency pins and automatic research-package discovery |
| [#12](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/12) | Fixed causal history features; target labels/code and identity vocabularies excluded |
| [#13](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/13) | Probability/ranking metrics, tied-score behavior and equal-student summaries |
| [#14](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/14) | Rate artifact provenance/integrity; review caught mutable nested payload, predictions now recheck hash |
| [#16](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/16) | Shared-parameter BKT grid baseline; simplified multi-concept assumptions documented |
| [#15](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/15) | Train-only standardized logistic model with portable inference and explicit convergence failure |
| [#17](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/17) | Reproducible synthetic rate runs; validation-only evaluation, test examples never parsed |
| [#18](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/18) | Optional pinned CPU PyTorch and dedicated neural CI |
| [#19](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/19) | Causal ID-only DKT batching/forward; 170 final-head tests, including all 15 neural tests |
| [#21](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/21) | Logistic/BKT portable artifact envelopes, live integrity checks and rate compatibility |

## October 13, 2026 — family processing integration

| Merged PR | Progress / decision |
|---|---|
| [#20](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/20) | Processing CLI now persists audited family holdouts; independent review passed, and the coordinator corrected a documentation example that lacked three observed families |
| [#22](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/22) | Substantive PR documentation and ongoing chronological records required throughout the project; independent review checked actual merge order and dates |
| [#23](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/23) | Authenticated release/terms observations and three failed empty transfers recorded; review clarified prior-session observations versus recording date |
| [#24](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/24) | Fixed-width reliability/ECE diagnostics with equal-student weights; independent review caught nonbinary floating-edge assignment, fixed using declared boundaries with regression tests |
| [#25](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/25) | Shared synthetic bundle validator supports student/family rate runs; review reproduced cross-partition learner sequence collisions, fixed without reading test examples |

PR #20 merged at 01:39 UTC October 14, which is October 13 in the client's
America/Toronto timezone. All final-head Python, web, browser replay and neural
checks passed. At the PR #20 merge, training integration for family bundles was
still separate work; PR #25 subsequently added family-aware rate runs.

## Current access and implementation gates

The user created a DataShop account after a required sign-in handoff. The account
session exposed the official Spring 2019 full release listing
`S19_All_Release_2_10_22.zip` (v1.0, posted February 10, 2022). Posted service
[terms](https://pslcdatashop.web.cmu.edu/Terms) restrict use to research and forbid
redistribution of downloaded data. Raw student data/code must remain private.

The first browser download and a subsequent authenticated download produced
zero-byte files. They failed ZIP validation and are **not** an acquired dataset.
Release acquisition, checksums, contents, catalog availability and actual grading
audit remain unresolved until a valid archive is obtained. No empirical metrics
or trained real-data model is claimed. See [access log](data-access.md).

## October 14, 2026 — continuing work and review

The user requested another browser-controlled download attempt instead of a manual
file download. Browser control became available again, initially with DataShop
signed out. The user completed authentication after the required handoff;
the computer-use guidance prohibits automating authentication dialogs. Download
then proceeded through the official S19 link, but the returned archive stayed
zero bytes and failed ZIP validation. The official format PDF also returned an
empty file. A media-download API retry timed out after 45 seconds. No usable
archive or release receipt exists; the transfer failure cause is unknown.

| Merged PR | Progress / decision |
|---|---|
| [#27](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/27) | Portable validation-fitted scalar grid temperature scaling; review fixed finite-loss summation overflow, with an extreme-value regression and 26 focused tests |
| [#26](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/26) | Strict CPU tensor-only DKT checkpoints, unknown-candidate training-rate fallback and live tensor fingerprint; review caught mutable loaded weights, fixed and independently rechecked with 36 focused tests |
| [#28](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/28) | Ongoing ledger updated; independent review corrected stale session and family-training statements |
| [#29](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/29) | Logistic/BKT synthetic training commands publish portable models, validation metrics and reproducible run metadata; 20 independent focused tests |
| [#30](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/30) | Label-free baseline inference adapter rejects candidate responses and revalidates causal history; 14 independent focused tests and optional-import check |
| [#31](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/31) | Deterministic CPU DKT training with validation patience and selected checkpoint parity; 50 independent focused tests, train-only vocabulary and explicit unseen-ID population fallback |
| [#32](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/32) | Opt-in synthetic baseline research API; browser CI caught missing editable engine install, repaired before rollout; 27 independent API/demo tests |

Checkpoint PR #26 and trainer PR #31 merged after final-head CI passed; empirical
research deliverables remain separate. Checkpoint review found mutable loaded neural
weights could change predictions while retaining saved metadata; a live-state
fingerprint guard and regression passed 36 focused tests and independent review.
Calibration review found
overflow while summing finite extreme losses before averaging; the corrected
implementation averages terms before summation and passes an independent review
with 26 focused tests. PR #27 merged after final-head CI passed; run/artifact/API
calibration integration remains a separate PR. Synthetic calibration smoke checks
are not empirical calibration evidence.

Work proceeds on checkpoint/training integration, baseline workflows and
product improvements in additional focused PRs. Append their merged outcomes and
meaningful review findings here as they happen; do not equate forward-pass tests
or synthetic training smoke results with completed research evaluation.

## October 14, 2026 — folder organization and pause

The user paused feature work and required project folders inside
`Personalized Programming Practice Engine`. All 23 sibling Git worktrees were
moved into ignored `.worktrees/` using `git worktree move`; the main checkout
remains at the project root. Branches, HEADs, Git status and hashes of changed or
untracked files were preserved, including unfinished embedding-cache and research
inspector work. No project worktree remains directly under the parent OneDrive
directory.

The local private storage folder was moved into ignored `.data/private/`; it
contains only an empty failed archive, not a usable release. A local move receipt
is retained under ignored `artifacts/`. Future worktree/storage locations are
documented in `AGENTS.md`. Feature development and agent implementation remain
paused until the user requests continuation.

## October 17, 2026 — resumed segmented development

The user resumed the project. The coordinator restored the three-person workflow
from the contained worktrees: the product engineer continues the optional fitted
baseline inspector; the model engineer continues the frozen embedding-cache
boundary; the coordinator owns calibration artifact integration, data access and
ordered PR rollout. Unfinished files were preserved across the folder move.

The earlier progress-document PR is being reconciled with the merged folder
maintenance instructions. Work stays inside `.worktrees/`; private data stays
inside ignored `.data/private/data/`. No usable real release or real-data results
are currently recorded. Each resumed feature retains its own tests, documentation,
independent review and PR rather than becoming a combined continuation PR.


### Reviewed deliveries on October 17

The folder-maintenance change was delivered in [PR #34](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/34);
[PR #33](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/33)
reconciled the delivery record after resumption. The following focused changes
were independently reviewed and merged after their final-head CI passed:

- [#35 embedding cache](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/35):
  exact content/configuration identities, finite immutable vectors and atomic
  no-overwrite publication. Baseline engineer independently reviewed the boundary;
  26 focused tests passed. Caller-provided vectors do not prove encoder execution.
- [#37 calibrated envelopes](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/37):
  bind a portable baseline, validation-fitting record and scalar in a checked
  artifact. Model engineer reviewed 62 focused artifact/scalar checks; coordinator
  ran 79 regressions. Hashes identify content, not authenticated provenance.
- [#36 research inspector](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/36):
  optional causal, label-free baseline inspection without changing replay ranking.
  Review caught truthiness checks that accepted missing/string flags; exact boolean
  checks and six malformed-flag browser cases fixed that finding. All ten browser
  scenarios and the build passed before final independent approval.
- [#38 validation calibration command](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/38):
  reload an existing baseline, verify bundle provenance, fit only on validation
  and publish artifact/reliability/run records. Independent baseline review passed
  14 workflow tests; broader checks passed 99 with three expected protocol skips.
  Before/after diagnostics use fitting observations, not independent reliability evidence.
- [#39 encoder environment](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/39):
  optional pinned dependencies and offline CPU CI. Independent review checked
  imports, dependency consistency and lazy API imports; 63 regressions passed.
  This installs software, not model weights or a real dataset.
- [#40 calibrated research API](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/40):
  serve known synthetic calibrated envelopes with explicit scalar/fitting metadata,
  preserving label-free inputs and unchanged replay behavior. Model engineer
  independently approved the final head after 52 focused API/serving checks.

[#41 snapshot storage](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/41)
merged after corrected-head CI and independent rereview. Review found that valid
JSON could carry a different record identity than its database row; row/payload
ID and timestamp binding plus regressions resolved it. The model engineer reran
37 storage/API tests and approved the corrected head. Storage alone does not yet
record API generation; that integration is a separate focused change.
The product engineer owns a separate calibrated-inspector PR; the model engineer
owns a frozen CodeBERT extraction PR. Neither is recorded as merged here.

No usable CodeWorkout release has been obtained: prior archive downloads contain
zero bytes. DataShop authentication is pending again; an account's existence does
not supply a usable release. Real import verification, statement/concept coverage,
real training, locked-test evaluation and learning-effectiveness evidence remain
unmet gates. Software tests and synthetic calibration runs do not satisfy them.


### October 17: calibrated presentation, generation records and frozen encoder

- [#43 calibrated inspector](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/43)
  merged after coordinator review, independent build/16 calibration browser cases,
  author full 20 browser cases and final-head CI. Explicit scalar/validation-fit
  labels avoid implying independently established reliability. The initial local
  reviewer run used system Python and could not import the package; rerunning with
  the documented shared environment passed.
- [#44 generation recording](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/44)
  merged after model engineer review, 65 independently rerun API/storage/research
  tests and final-head CI. Each response references the exact stored ordered
  ranking and history position. GET records generation; retries can add records.
  Generation does not establish display or choice.
- [#45 frozen CodeBERT](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/45)
  merged after coordinator review, 35 independent adapter/cache tests and final-head
  CI. Review found that an extra unverified tokenizer file could shadow checked
  vocabulary; the final snapshot guard and regression reject unexpected files.
  The official 498,627,950-byte weights were downloaded privately and matched the
  expected SHA-256. Frozen CPU inference on three original synthetic content inputs
  produced finite 768-dimensional vectors and identical cache-hit reloads in a
  29.23-second smoke run. A receipt stays in ignored private encoder storage.
  This establishes local encoder execution, not predictive quality. Source MIT
  terms and absent checkpoint-specific license metadata remain distinguished.

The next segmented work is choice backend #46, an explicit product choice action,
and content-model batching followed by a separate forward network. Choice events
remain separate from simulated correctness. The engineers agreed that browsing a
prompt or accepting a default selection must not automatically record a choice.
The [research engineering status](../reports/research-engineering-status.md)
aggregates work-unit acceptance without claiming blocked experiments are complete.


### October 17: causal sequences, explicit choices and timing

- [#49 content batches](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/49)
  merged after coordinator review, 49 independent content/encoder/cache checks and
  final-head CI. Training-only immutable concept IDs and exact frozen vector
  identities feed padded causal histories; target labels remain separate.
- [#51 workspace loading](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/51)
  fixes overlapping StrictMode snapshot requests publishing stale success, errors
  or loading completion. Browser CI on other PRs exposed duplicate research
  requests; the team fixed the source race rather than relaxing count assertions.
  Four deterministic regressions passed independent review; an original-code
  negative control reproduced stale data. Final-head CI passed before merge.
- [#46 choice backend](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/46)
  retains explicit candidate choices against intact generated snapshots, separately
  from grades. Product engineer independently ran 51 storage/API checks and
  rereviewed the unchanged feature after integrating #51. Both final browser
  workflows and all other final-head checks passed before merge.
- [#50 label-free DKT](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/50)
  adapts already-loaded checkpoints without adding Torch to generic API imports.
  Model engineer independently ran 28 adapter/checkpoint checks and rereviewed
  the unchanged feature after #51 integration. Final-head CI passed before merge.
- [#52 inference profiling](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/52)
  measures repeated loaded synthetic baseline batches and binds exact input/artifact
  bytes. Product engineer independently ran 17 profile checks; all final-head CI
  passed before merge. Local timing is distinct from predictive quality.
- [#53 content forward](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/53)
  merged after coordinator review, 34 independent content input/forward checks and
  final-head CI. Masked packed history and candidate content condition untrained
  logits; frozen vectors receive no gradients. A separate private smoke used actual
  cached original-synthetic CodeBERT vectors and produced finite, label-invariant
  untrained logits. No training or measured benefit is established.

The integrated suite at encoder merge `25ae62b` passed 459 tests with three
expected protocol skips. Later focused changes have their own final-head checks
above; this historical total is not presented as the latest suite count.
[The product choice UI #48](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/48)
merged after final-head CI and coordinator review: seven independent mocked choice
cases and both live choice/replay scenarios passed; the author ran all 32 browser
scenarios and the build. The real endpoint acknowledged the exact displayed
snapshot/problem while history/profile/attempts remained unchanged. Content checkpoint work
is a separate model-engineer segment. Optional choice-to-attempt linkage is a
separate coordinator/product contract, preserving grading as its own event.

DataShop remains at sign-in. The browser tab was replaced; reconnecting to the
observed login tab timed out twice on focus setup. No authentication was automated,
no archive was acquired, and the release/catalog/real-training gates remain open.
All project worktrees and private encoder artifacts remain inside the project root.


### October 17: content training foundations and policy records

- [#55 content checkpoints](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/55)
  merged after independent coordinator review and final-head CI. Review reproduced
  loading failure under an ambient meta device; explicit CPU restoration now
  preserves caller device/RNG context. The coordinator ran 72 related checks;
  the owner ran 128. Checkpoints bind architecture, vocabulary, encoder,
  provenance and tensor integrity without activating a served model.
- [#56 choice/attempt linkage](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/56)
  binds one explicit choice and matching simulated outcome transactionally.
  Same-payload retries return the original result; conflicts do not append rows.
  Independent product review and final-head CI passed. Unknown catalog exercise
  behavior was clarified separately from a known mismatched choice exercise.
- [#58 offline content cache preparation](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/58)
  verifies the synthetic bundle before encoder work, caches train/validation
  content and returns an aggregate inventory receipt without parsing test rows.
  Model-engineer independent review and final-head CI passed. An actual private
  smoke used the original synthetic fixture: 8 train/2 validation examples,
  three cached content entries, 83.11 seconds including encoder initialization.
- [#57 optional outcome linkage UI](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/57)
  merged after coordinator review, ten independent selected browser cases,
  the owner's full 40-case suite and final-head CI. A real endpoint check
  confirmed that retrying the same choice produced one history row. Pending or
  absent acknowledgement remains ordinary unlinked replay; failures never silently
  fall back to an unlinked outcome.
- [#59 content optimizer](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/59)
  adds bounded CPU training, train-only concepts, validation-only early selection
  and restored caller random/thread/determinism state. Independent coordinator
  review and final-head CI passed. The in-memory optimizer neither publishes a
  run nor evaluates test examples; run publication is separate PR #60.
- [#61 configurable heuristic policy](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/61)
  merged after independent product review, 42 policy/snapshot checks and all
  final-head CI. Exact normalized parameters and canonical hashes are retained
  with each generated snapshot. Review caught acceptance of missing v2 policy
  identity; corrected validation and regression reject it while preserving v1
  history. The default 60-80% band and bounded weights are untrained hypotheses,
  with no measured learning benefit. Optional UI disclosure is separate PR #62.

The next independent segments are reviewed synthetic content-run publication,
optional policy inspection and a local container recipe. A three-epoch private
run with actual cached original-synthetic vectors has exact checkpoint replay;
this is software execution evidence, not real-data quality. Container builds and
local proxy/retry/restart/Swagger checks passed on separate draft PR #63. No usable
CodeWorkout release or verified real-data catalog has been acquired; those gates
remain open. All private artifacts and worktrees remain project-contained.


[#60 synthetic content runs](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/60)
merged after coordinator review, 100 independent related checks (three expected
protocol skips) and all final-head CI. Review replaced metric filtering with an
explicit aggregate whitelist and enforced one-thread deterministic reload parity
while restoring caller settings on success/failure. The owner ran 111 related
checks and repeated the private three-epoch actual-vector synthetic smoke with
exact parity. Publication is atomic into a new directory; test rows stay unread.
No real-data result, calibration or model-serving activation follows from this.

### October 17: local rollout and loaded content inference

- [#63 local containers](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/63)
  merged after two independent recipe reviews and all final-head checks. Actual
  builds and isolated HTTP checks verified the frontend/API proxy, explicit
  choice, linked outcome/exact retry, API restart persistence and Swagger schema.
  Review added raw-data/database build-context exclusions and corrected Swagger's
  proxy root path. Runtime images exclude private state and optional ML packages.
- [#66 label-free content adapter](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/66)
  merged after coordinator review, 91 independent related checks and all
  final-head CI. Already-loaded checkpoints derive vocabulary/encoder identity
  from metadata and consume exact supplied cached entries. Queries are detached
  and revalidated; ordered finite scores require live integrity even for empty
  batches. There is no file/network loading, encoder initialization or API
  activation. A private actual-vector synthetic smoke matched direct inference.
- [#62 policy disclosure](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/62)
  merged after coordinator review and final-head CI. Fifteen independent guarded
  metadata cases passed; a separate real-backend browser check matched displayed
  configuration/hash to the generated response. The owner ran all 56 browser
  cases. Configured challenge bands remain hypotheses without measured benefit.
- [#65 container CI](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/65)
  merged after independent product/model review and final-head checks. Real Linux
  builds checked proxy/schema, choice without grading, exact linked retry and
  conflict rejection, then removed/recreated containers and verified persisted
  history and the original retry receipt. Initial CI exposed root-owned parent
  directories preventing the host receipt write; precreating directories as the
  host fixes the cause. An independent isolated Linux UID1000 experiment
  reproduced both failure and fix. Final container jobs passed in 31/34 seconds.

Separate docs PR #64 records the prior model/policy progression; this entry keeps
the later rollout chronological. The integrated Python suite at `0331822` passed 644 tests with three expected
protocol skips in 157.48 seconds. Later documentation-only #67 does not change
that tested implementation.
Next segments are the bounded loaded-content profiler and a scoped contrast fix,
each with a separate owner/PR. Real release verification, selected-model locked
tests, independent calibration evidence and learning outcomes remain unmet.

[#67 synthetic walkthrough](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/67)
merged after coordinator source/final-delta review and all final-head CI. The
product engineer verified three clean-seed live replay/choice/linkage cases and
the real v2 policy disclosure case; guide links and contained Compose configuration
also passed. Setup preserves an existing demo using a separate private bind
directory/project/port. Inspection, explicit choice, simulated outcomes and
duplicate-request receipts are explained as separate behaviors. No model or
real-data completion is claimed. A subsequent product audit found low contrast
in several small evidence/status/history labels; a focused fix is underway.


A later DataShop browser recheck still lists the login page. Binding that observed
tab again failed after10 seconds during browser focus setup; no authentication or
download was performed. The previously requested manual sign-in and working
browser connection remain external dependencies. No usable release was acquired.

[#68 offline content profiling](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/68)
merged after coordinator review, 98 independent related checks and all final-head
CI. Bounded label-free queries and exact offline entries bind checkpoint/query/cache
identities. Load, parse, cache and warmup costs are separate from aggregate
loaded-adapter timings; feature building and live integrity stay inside samples.
Caller CPU settings/RNG are restored on failure/success. The private two-query
actual-vector smoke is software evidence, not representative compute or model quality.

[#70 text contrast](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/70)
merged after coordinator source/mobile visual review, an independent real-DOM
contrast check and all final-head CI. Nine color declarations now meet the
normal-text threshold on actual initial/hover/selected/mobile surfaces; original
failures were reproduced. Layout/actions are preserved. This targeted correction
does not assert complete accessibility conformance.

The three-engineer review found no further concrete product release defect.
Remaining planned acceptance requires verified real data/catalog and its causal
audit, locked partitions, fair comparative validation/ablations/compute records,
validation-only selection/calibration, untouched-test/grouped-error reporting and
clean-machine reproduction of that actual research. Selected-model activation,
concept probes and result views depend on that evidence. Learning effectiveness
still requires a prospective study. Current synthetic-only software and toy timing
smokes do not close these gates; no new features were invented to obscure them.


### October 18: official release acquired, import gates remain

The user restored DataShop authentication and the browser connection worked.
The official S19 full release (file 27181, posted February 10, 2022) downloaded as a
nonempty 7,927,271-byte ZIP and passed full CRC verification. SHA256:
`c0c21654766c05da4f1beb691ca152181e3b08679855dc70ea7cea01a500cec1`.
The verified archive, safe extraction and member-hash receipt stay inside ignored
project-private storage; no new acquired archive remains in Downloads. Current
project terms point to DataShop's noncommercial-research/non-redistribution rules.

Independent data/model engineers reviewed source gates and private structural
compatibility. Naive timestamps, mixed timezone representations, scored timestamp
ties and restricted Order disagreements require source-backed chronology review;
checks cannot be bypassed to make an importer run. Current source provenance,
training and serving gates remain unchanged. No real canonical data or model run
was created. Catalog/source research and a separate bounded archive-inspection
utility are independent next segments; exact current evidence is maintained in
[release-acquisition.md](release-acquisition.md).


[#71 acquisition record](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/71)
merged after independent model-engineer verification of the actual archive,
five-document review and all final-head CI. README/status distinguish successful
private acquisition from unchanged real-import/model gates. No raw data, catalog
content, account email or session material was published.

Subsequent independent source/catalog audit located the exact organizer-linked
sheet: 50 problem prompts and 18 binary annotation columns. An explicitly narrow
assignment spelling crosswalk gives complete 50/50 coverage; no generic numeric
identifier conversion or instructor-ground-truth claim is allowed. Original CSV
and audit/coverage receipts stay private. The archive inspector and catalog mapper
are separate small engineering segments.

The timezone review found a substantive unresolved issue: naive timestamps have
mixed 0/UTC labels for most subjects, while the archived organizer wording does
not establish whether 0 is UTC or relative to Eastern time. Formal scoped Order
cannot resolve cross-problem chronology. Label-blind sensitivity checks establish
that interpretation affects history order; they do not select a policy. A private
clarification draft is ready and sending it awaits explicit user authorization.
[Source evidence and limits](catalog-chronology-audit.md) are maintained separately.
No canonical real histories, real-source provenance flags or training run was made.


[#72 bounded archive inspection](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/72)
merged after coordinator source review, 42 independent archive/import/manifest
checks and all final-head CI. An independent private official-archive smoke matched
the acquisition archive SHA and all six file hashes. The narrow profile permits
only the six CSV members and three known empty directory markers, preflights ZIP
directory allocation and streams bounded CRC/hashes. It never parses rows, extracts
files or authorizes real-data provenance/training. Only original synthetic ZIP
fixtures are committed.


[#73 organizer catalog mapping](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/73)
merged after coordinator source review, 98 independent related checks (three
expected protocol skips) and all final-head CI. Independent private replay matched
all 50 saved candidate values exactly, preserving release IDs, prompt text and
original positive concept headers. The frozen result has detached receipt metadata
binding source/inventory/crosswalk/policy/candidate hashes. Only original synthetic
CSV fixtures are public; mapped actual candidate JSON and receipts remain private.
No interaction import, timezone normalization, source flags or training was added.

Integrated data checks at `06f518d` passed 115 cases with three expected protocol
skips in 15.19 seconds, covering both new modules plus importer/manifest/bundle
boundaries. Private original-archive and 50-candidate replays passed independently.
Real chronology and training still await authoritative timezone clarification; the
prepared email remains unsent pending the user's explicit authorization.

## October 18 reproducible audit rollout

[#75 comparative-study protocol](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/75)
merged after independent model/data-engineer review of exact head `2196784`,
relative-link verification and all applicable final-head CI. It declares primary
validation log-loss ranking, fixed seed/configuration and incomplete-run handling,
calibration separation and locked-test reporting before real metrics exist.
Resource ceilings, real-source support and the test/bootstrap evaluator remain
explicitly pending. No training, results or publication rights are implied.

[#76 chronology aggregates](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/76)
merged after independent coordinator source review, 33 final collector checks
and all final-head CI. Review corrected maximum tie size for singleton-only inputs
and clarified that invalid-Order rows are excluded from the ordered sequence.
The label-free projected interface produces fixed aggregate keys, distinguishes
raw wall-time decreases from same-literal observations, and never converts zones
or creates histories. Private official projections reproduced 272 Run timestamp
tie groups (673 rows), 403 mixed-literal learners and three scoped wall-time
decreases; all three are within one literal. These are source diagnostics, not a
verified causal timeline. Source-backed chronology remains unresolved.

[#77 structural auditor](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/77)
merged after independent coordinator source/contract review, 45 related checks and
all final-head CI. Independent private replay matched acquisition hashes for both
tables, 201,570 MainTable records and 69,627 CodeState records, with zero key/join
diagnostics and all Run scores finite/in-range. Its API/CLI reads only those two
tables and emits fixed aggregate diagnostics, including unavailable-field `null`
values; unknown headers/events and private rows never enter receipts. Hash stability
is per table, not an atomic two-table snapshot. The receipt remains private; no
outcome distribution, chronology policy or real-source training gate was added.

The documentation rollout record and acquisition/continuing-work links merged in
[#78](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/78)
after independent model/data-engineer review and all applicable final-head CI.
Integrated Python verification at `d2ecb9c` passed **787 tests, three expected
skips**, in 172.30 seconds. Main CI, neural/encoder checks, browser smoke and local
container workflows also passed at that revision. No empirical model result or
learning-effect claim follows from these software checks.

[#79 chronology CSV adapter](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/79)
merged after independent calibration-engineer review with 76 related checks,
coordinator supplementary review with 51 adapter/collector checks, private source
hash/aggregate parity and all final-head CI. It projects seven exact string fields
from MainTable and verifies v6 metadata's declared restricted scope; byte/row caps
and generic errors bound the local CSV interface. Observed consistency `true`
does not approve a timeline: interpretation remains unresolved and no zone
normalization, canonical import or real-source training is enabled.

[#80 paired student bootstrap](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/80)
merged after independent platform-engineer review, 39 related checks and all
final-head CI. A separate expanded-row/statistics-quantile calculation reproduced
all 12 interval outputs over 200 seeded draws with unequal clusters, both labels
and boundary probabilities. Review found and corrected non-string student IDs in
copied model objects, adding `None`/integer regressions. The pure utility preserves
whole-student draw multiplicity for observation/equal-student log-loss/Brier and
paired differences. It returns aggregate estimates only and reads no files;
locked-test access, ranking-metric intervals and empirical results remain separate.

Integrated checks at `7b8da45` passed 110 audit/adapter/bootstrap/metric cases in
1.43 seconds. Real interaction import/model comparison still requires authoritative
chronology and reviewed real-source support. The prepared organizer clarification
email remains unsent pending explicit sending authorization; no contact or student
data transmission occurred during these engineering PRs.

## October 18 HOME desktop handover verification

The corrected project directory was freshly cloned at clean main `72725ca`.
Remote checks confirm PRs #75-81 merged, no open PRs at inspection, and successful
CI/browser/neural-encoder workflows on that exact head. No local checkout was
overwritten. The private CodeWorkout release directory is absent on this desktop;
previous acquisition evidence describes the earlier machine, not files available
in this clone. No archive/catalog was redownloaded and no outreach occurred.

A three-engineer team is implementing bounded DKT validation/reload batches and
pure paired ranking-metric bootstrap intervals in separate contained worktrees.
Purpose, owners, acceptance and dependencies are recorded before implementation
in the feature contracts and continuing-work plan. Current GitHub authentication
is read-only for this repository, so publication and integration are blocked
pending writer access. Local work must not be called merged or CI-verified.

Local verification: the model engineer's ranking segment passed 61 focused
ranking/bootstrap/metric checks, and the independent platform reviewer reran the
same 61 checks with no blocking findings. The platform engineer's DKT segment
passed 59 training/forward/checkpoint/serving checks; independent model-engineer
source review found no blocking defects. These are original synthetic software
checks. Final commit review and remote CI remain required before integration.

The clean main baseline at `72725ca` passed **828 tests, three expected skips**
in 92.50 seconds on this desktop with Python 3.12.13 and the pinned development,
CPU neural and encoder dependencies. This verifies current main, not the new
feature heads. The reviewed local commits are `3a21b0c` on
`feat/paired-ranking-bootstrap` and `6f0e039` on `fix/dkt-validation-batches`.
Both have focused local checks and saved draft PR descriptions. Neither is pushed
or merged; final-head GitHub checks cannot run until write authentication is ready.

The model engineer independently reran 52 DKT training/forward/checkpoint tests
at final local head `6f0e039`: all passed in 14.27 seconds, with no review findings.
The coordinator's local documentation diff was independently reviewed for factual
accuracy, privacy and unmerged-work disclosure with no findings. This is agent
review, not a human GitHub approval; remote final-head CI remains pending.

## October 18 resumed HOME publication

After the user completed GitHub login and resumed work, repository push access
was verified without changing credentials. Refreshed origin/main remains
`72725ca`; no preexisting open PRs or local checkout edits were found. The prior
read-only authentication blocker is resolved. Private release assets remain
absent here; no redownload, organizer outreach, real import or training occurred.

The reviewed ranking and DKT branches were published initially as draft PRs
[#82](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/82)
and [#83](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/83).
Exact final-head checks and current local reruns are pending before rollout.

### Reviewed HOME code rollout

[#82 ranking uncertainty](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/82)
squash-merged as `4908aa1` after independent exact-head review and all ten
applicable final-head checks succeeded. Current local replay passed 61 focused
checks; the independent platform reviewer had also passed 61. The utility reports
paired whole-student ROC AUC/incorrect-positive AP intervals with explicit one-class
replicate counts and conditional-interval limits. It adds no evaluator or test access.

[#83 bounded DKT validation](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/83)
squash-merged as `ad08774` after independent exact-head model review and all ten
applicable final-head checks succeeded. Current local verification passed 59
focused cases; independent model execution passed 52. Validation and selected
checkpoint reload respect the configured batch size while preserving ordered
predictions, unknown-ID fallback and aggregate early-selection semantics. This
bounds rows per padded tensor, not total data/history memory or run time.

Main was fast-forwarded cleanly to `ad08774`. The next separate reviewed segment,
[#85 history-length summaries](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/85),
implements the protocol's fixed reporting strata without a loader. Author and
independent platform reviewer each passed 33 focused checks at `791a059`; final-head
GitHub checks remain pending before this segment can be called delivered.

[#85 history-length summaries](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/85)
squash-merged as `e4f4e84` after independent approval of exact head `791a059` and
all ten applicable final-head checks succeeded. Both author and platform reviewer
passed 33 focused cases. The pure utility uses existing observation-weighted
metrics for history lengths 0, 1-4, 5-19 and 20+, validates all inputs before
binning and reports explicit empty/one-class results without row or student IDs.
It does not read files, certify causal histories or unlock test access.

Main was fast-forwarded cleanly to `e4f4e84`; full integrated Python verification
is running with pinned optional dependencies and offline encoder settings.
The team assessed remaining work: private release/catalog/encoder assets are
absent here; source-backed chronology, reviewed real-source manifests/loaders,
resource pilot/ceilings and validation selection precede empirical calibration,
locked-test evaluation, results and final research reproduction. No further
independent feature is clearly needed without speculating about these contracts.

Integrated verification at exact code head `e4f4e8420904bdf701a0b358304dea80d817c5cf`
passed **869 tests, three expected skips**, in 87.14 seconds with the pinned
Python 3.12.13 development/CPU-neural/encoder environment. The initial invocation
specified a missing test-temp parent and failed fixture setup; rerunning with the
corrected project-contained `.data/qa-final` directory passed without source edits.
The successful output is retained in ignored local verification artifacts.
All relative links across the four rollout documents resolve, and whitespace
checks pass. Coordinator documentation is delivered separately through
[#84](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/84),
with independent final-head review and CI required before its squash merge.

These checks establish integrated synthetic software behavior only. Real-source
import/training, locked-test results, learning claims and organizer outreach remain
unperformed. The private source/chronology/resource/selection dependencies above
are the remaining research blockers, not unresolved GitHub authentication.

## October 19, 2026 (UTC): renewed desktop reliability review

Refreshed origin/main remains `1d172b2`; no open PRs or uncommitted checkout changes
were found. Existing feature worktrees were preserved and new isolated branches
created for a requested three-engineer reassessment. Two actual synthetic
reproductions identify dependency-ready fixes: partial data-bundle overwrite on a
failed CLI rerun, and DKT checkpoint restoration altering RNG/failing under an
alternate default device. Purpose, owners, acceptance and dependencies are recorded
in continuing-work and feature contracts before implementation. Neither issue
requires private data or relaxation of the empirical gates.

The coordinator is also rehearsing a wheel installation in a fresh runtime-only
environment outside checkout imports. Wheel construction succeeded; initial
cache-only dependency installation lacked a pinned public package and was retried
from the normal public index. This is an installation smoke, not a real-data run.
No private assets, weights, imports/training or outreach were used.

## October 19, 2026 (UTC): reliability review and installed-wheel evidence

The two reproduced fixes are published independently as initially draft
[#86](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/86)
and [#87](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/87).
Platform engineer approved DKT exact head `70b24a0` with no findings; author and
coordinator independently passed 47 checkpoint/training/serving tests (15.42 and
15.30 seconds). Automatic review rejected the reviewer's execution command over
its temporary-output ownership interpretation; coordinator-owned verification
passed without changing the implementation. Model engineer approved processing
exact head `b194d40` with no findings and independently reproduced 45 passed,
four Windows platform skips (19.46 seconds); author also passed 76 downstream
checks (51.39 seconds). Initial downstream failures came from Windows temporary
path length and passed with contained extended-length paths. Both PRs require
successful exact-final-head remote checks before merge.

The coordinator built a wheel from `1d172b2` and installed it into a fresh
runtime-only environment with the pinned runtime lock. From an artifact working
directory, isolated Python (`-I`) imported the API and package from the installed
wheel, with no Torch/Transformers/sklearn/NumPy imports. The installed CLI processed
original synthetic examples, fitted a rate model, fitted validation-only
calibration, and reloaded its saved artifact with identical predictions. Runtime
dependency verification passed for all 14 installed packages. The first existing
fixture correctly rejected calibration because its two validation observations
had one class; a separate original 20-row/10-student fixture with both classes
completed the rehearsal (16 train, two validation observations). No test examples
were evaluated. Outputs explicitly retain `research_results=false` and
`test_evaluated=false`; this is packaging/software evidence, not research quality
or a clean operating-system installation. Ignored evidence is retained under
`artifacts/wheel-rehearsal/` and `.data/qa-wheel-runtime/`.
