# Atomic processing bundles

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
