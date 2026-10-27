# Atomic processing bundles

October 27 CodeWorkout source consistency plan — Owner: data engineer. Purpose:
prevent an imported label from being published with a source hash taken from
different table bytes. Acceptance: hash the required MainTable/catalog and the
presence/content of optional CodeStates before and after import and before
publication; reject any observed change without publishing an output. A synthetic
after-parse score mutation must fail, while an unchanged synthetic import retains
its source hashes. Dependencies: existing CodeWorkout adapter, processing CLI and
atomic publication. This adds no real-source permission or chronology decision.

The CodeWorkout CLI now compares the MainTable, catalog and optional CodeStates
file set and SHA-256 values before/after parsing and again before publication.
The import receipt retains the initial source hashes only when those checks agree;
an observed source change discards staging. These checks detect changes at their
read points but do not create an atomic filesystem snapshot.

October 27 causal-prefix completeness plan — Owner: platform/API engineer.
Purpose: reject a hash-valid synthetic training bundle whose example silently
omits an earlier scored first attempt from its observed history. Dependency:
the existing student and family split processing contracts and training loader.
Acceptance: each train/validation example contains exactly the earlier scored
first-attempt positions permitted by its protocol. Student splits use all earlier
targets for that student; family splits use earlier training-family targets only.
Retry sequence gaps and earlier held-out family targets remain valid gaps.
Existing history content/label consistency and test-partition exclusion remain
enforced. Synthetic regressions cover missing earlier targets in train and
validation for both protocols, plus valid retry and held-out gaps. No real data,
empirical result, or protocol change is implied.

The loader now compares each example's history sequence positions with the
complete permitted prefix reconstructed from scored train/validation targets.
Existing checks still verify the content and label of each observed row, and
the locked test partition is never parsed for training. The synthetic regression
passes for both protocols and catches omissions in both training and validation;
the pre-integration cloud branch passed 974 Python tests with three expected skips. The
content replay batch fixture now uses distinct validation students because its
previous repeated same-student targets lacked their required earlier histories.

October 27 canonical ID fix plan — Owner: data engineer. Purpose: prevent the
processing CLI from publishing a hash-valid bundle that the training loader
rejects because a student ID contains only whitespace. Acceptance: canonical
`Interaction` validation rejects whitespace-only student IDs before the CLI
creates an output directory or manifest; the unchanged synthetic fixture still
processes and loads. Dependencies: existing canonical schema, processing CLI and
synthetic fixture. This check does not infer whether distinct nonblank IDs name
the same learner.

Canonical `Interaction.student_id` now requires at least one nonwhitespace
character. The synthetic CLI regression rejects a blank-ID source without an
output directory and confirms the original fixture still loads for training.

October 27 problem metadata consistency plan — Owner: data engineer. Purpose:
prevent one canonical problem ID from naming different statements or concept
sets across students. Acceptance: reject conflicts across every source
interaction, including retries, before publication; reject conflicts across
hash-valid train/validation targets and their permitted histories at training
load; keep test rows unread. Dependencies: existing canonical processing and
training-bundle contracts. Problem text must match exactly. Concept order may
vary because the research models use concept membership or an unordered mean.
The training loader verifies test artifact bytes through the manifest but does
not parse test examples, so it cannot compare metadata present only in test.
Candidate concept IDs must remain nonblank and unique before set comparison;
duplicates would otherwise change the content model's concept mean.

Owner: platform engineer. Purpose: preserve processing-bundle integrity when a
write fails or a command is repeated. Dependencies: existing data CLI, processing
manifest and synthetic fixtures; no source or chronology policy changes.

Plan recorded before implementation on October 19: reject any existing output
path, including broken symlinks; write the five processing artifacts and manifest
in a temporary sibling directory; publish the complete directory only after all
writes succeed. Failures remove staging and preserve any existing output.
Acceptance: synthetic real-CLI success retains identical artifact content;
reused paths stay unchanged; injected artifact/manifest failures expose no partial
output; temporary staging is cleaned. Independent review and final-head CI are
required before rollout.

Reproduction at main `1d172b2`: an isolated synthetic CLI run succeeded; a second
run changed only input trailing whitespace and encountered a directory occupying
`split.json`. It failed after overwriting `audit.json`, while the old manifest
remained. This demonstrated partial publication and invalidated bundle integrity.
No private data or real import/training was used.
Publication behavior: `--output` must name a path that does not exist, even when
it is an empty directory or a broken symlink. Reproduce an earlier bundle into a
new path rather than overwriting it. A sibling publish lock prevents two CLI
writers from publishing the same destination simultaneously; failure to acquire
it leaves the other writer's lock untouched. Ordinary write/publication failures
clean staging and the acquired lock. A forced process termination may leave a
staging directory/lock for manual inspection; no crash-recovery mechanism or
external-filesystem-writer coordination is claimed.

Verification: focused synthetic CLI/import/family/manifest/bundle checks passed
45 tests with four platform skips on this Windows host (including directory
symlink creation unavailable). Tests inject artifact, manifest and rename failures,
preserve a destination appearing during staging, and verify real subprocess
publication remains loadable. No private release or empirical run was involved.
Downstream synthetic rate/baseline/calibration/content-cache/content-run/DKT trainer
checks passed 76 tests in 51.39 seconds offline. An initial run used an ordinary
Windows path exceeding the cache temporary-file length limit (57 passed, five
failures and 14 setup errors); the identical source passed after supplying an
extended-length test path within this isolated checkout. No cache/model production
code was changed to accommodate the test harness.
