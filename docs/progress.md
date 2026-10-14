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
file download. Browser control is available again, but the current Chrome session
is signed out of DataShop. The login page is prepared for user authentication;
the computer-use guidance prohibits automating authentication dialogs. Download
and setup remain assigned to the coordinator after sign-in, with no usable archive
or release receipt yet.

| Merged PR | Progress / decision |
|---|---|
| [#27](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/27) | Portable validation-fitted scalar grid temperature scaling; review fixed finite-loss summation overflow, with an extreme-value regression and 26 focused tests |
| [#26](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/26) | Strict CPU tensor-only DKT checkpoints, unknown-candidate training-rate fallback and live tensor fingerprint; review caught mutable loaded weights, fixed and independently rechecked with 36 focused tests |

Checkpoint PR #26 merged after final-head CI passed; its trainer and empirical
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
