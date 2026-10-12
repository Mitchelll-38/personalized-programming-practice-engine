# Day 2 delivery

Executed October 12, 2026. Day 2 denotes the next sprint work unit; the original schedule places it on October 13.

## Ownership and segmented rollout

The coordinator owned instructions, artifact manifests, CLI integration and final review. The data engineer worked in an isolated worktree on event reconstruction and independently reviewed integration. The product engineer worked in another isolated worktree on learner evidence and then a separate browser-test branch. Every change went through a focused PR, independent agent review and CI; no day-two source changes were pushed directly to main.

| PR | Coherent change | Scope |
|---|---|---|
| [#1](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/1) | Project-wide engineering workflow | 55 added lines; AGENTS.md, PR template and documentation links |
| [#2](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/2) | Learner evidence and cold-start diagnostics | 99 additions / 12 deletions; additive API fields, UI and tests |
| [#3](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/3) | Versioned processing manifests and integrity checks | 113 additions / 3 deletions; explicit source declarations and artifact hashes |
| [#4](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/4) | Strict CodeWorkout format adapter | 285 additions / 5 deletions; module, tests, 17 synthetic fixture lines and source/label audit |
| [#5](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/5) | Importer CLI integration | 79 additions / 4 deletions; source hashes, processing reuse and integration tests |
| [#6](https://github.com/Mitchelll-38/personalized-programming-practice-engine/pull/6) | Live browser replay automation | 187 additions / 5 deletions, including 46 generated lockfile additions; lifecycle evidence in PR |

Instruction, feature and test PRs were kept separate. Dependent work was integrated after its foundations. Review comments identify the actual agent reviewer and distinguish agent review from human GitHub approval.

## Delivered behavior

- Import `Run.Program` events from the organizer-documented CSV layout with an explicit statement/concept catalog; reconstruct attempts rather than trust the supplied Attempt column. Compilation/test rows never become extra primary attempts.
- Reject missing/invalid grades, missing candidate metadata, ambiguous timestamps, unresolved code joins and duplicate event/code/header keys. A missing first grade cannot silently promote a later retry.
- Reuse canonical validation, causal histories and student-disjoint partitions through the data CLI. Import audits carry original CSV/catalog hashes and the actual adapter label/order definitions.
- Processing manifests identify dataset/schema/feature/split versions and verify all five output hashes. Unspecified provenance remains unverified; no trained model or permission is implied.
- Dashboard shows all interactions versus distinct first attempts versus excluded retries; each concept exposes its supporting exercises and a no-history/limited-history label. Zero evidence is explicitly a neutral prior with no personal evidence. Labels describe volume, not statistical confidence.
- The browser smoke test exercises the actual React/API replay, evidence changes, retry exclusion and persistence with an isolated synthetic database. See [browser test instructions](../docs/browser-smoke.md).

## Verification and review findings

- Integrated Python suite: **47 passed**. Coverage includes causal boundaries, grading/reconstruction rejection, output provenance/integrity, API persistence/concurrency and CLI integration.
- The data review caught duplicate CSV headers silently overwriting grading fields. Fixed with fail-closed parsing and a regression test before merging #4.
- Frontend production build passed. Live Chromium smoke: **1 passed in 12.4 seconds**, clean automatic exit on Windows, and test ports released. An initial npm-wrapper shutdown hang was resolved by launching Vite directly before merging #6.
- Each PR records its local verification and final-head GitHub checks. Main CI repeats the Python tests, fixture CLI and web build; browser CI runs Chromium separately.

## Acceptance gates

| Day-two requirement | Status |
|---|---|
| Importer, reconstruction and grading contract | Implemented against organizer-documented format; validated on synthetic fixtures only |
| Dataset/feature versioning and model-state boundary | Implemented; no trained model artifact exists |
| CLI integration and source audit | Implemented and tested |
| Cold-start/supporting-history display | Implemented; estimates remain synthetic/untrained/uncalibrated |
| API-to-browser replay automation | Delivered through its separate reviewed PR |
| Exact real release, access/usage terms, counts and missingness audit | **Unmet external dependency** |
| Real exercise statement/concept provenance and grading/timestamp inspection | **Unmet external dependency** |

No real student dataset was downloaded or redistributed and no model was trained. Read-only Chrome inspection confirmed the public CodeWorkout DataShop listing and its login-gated file feature; release-specific terms and contents were not obtained. An adapter built from organizer documentation does not establish compatibility with an unseen release. See [data access evidence](../docs/data-access.md).

Day 3 can proceed with split/feature engineering on clearly labeled fixtures. Real-data experiments require an authorized local release, verified terms and statement/concept catalog first. The first-scored-run interpretation also needs confirmation against actual compilation/grading behavior before it is used for empirical claims.
