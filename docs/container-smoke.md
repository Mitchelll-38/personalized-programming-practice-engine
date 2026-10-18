# Container integration smoke

Owner: coordinator. Purpose: preserve local packaging behavior in CI after the
recipe PR #63. Acceptance: build both images; exercise static web, API proxy and
OpenAPI, explicit choice, linked outcome/idempotent retry, conflict rejection and
restart persistence; isolate private synthetic state and always clean containers.
Dependency: local container recipe. No dataset download or model activation.

Plan before implementation: a standard-library HTTP smoke script with replay and
post-restart verification phases, plus a narrowly triggered GitHub workflow.
Reuse the real API contract and fail on any HTTP/behavior mismatch. Keep this
separate from the image/runbook PR; no production load or predictive metric claim.

## Run against a separate local instance

Use an unused port, a unique Compose project (`-p`), and an absolute ignored private
data directory inside the project. Start the containers as in
[local-containers.md](local-containers.md). Then run:

```text
python scripts/container_smoke.py replay --base-url http://127.0.0.1:18081 --state .data/private/data/container-ci-receipt.json
```

Stop and recreate that Compose project without deleting its bind directory, wait
for health, then run the same command with `verify` instead of `replay`.
The receipt contains original synthetic history and identifiers, stays in ignored
private storage and is never uploaded by CI. The smoke appends one simulated
outcome; always use its separate database rather than a working demo database.

The workflow triggers on recipe, runtime-lock, app/source/web or smoke changes.
It builds on a fresh Linux runner, checks replay, removes/recreates containers,
checks persisted history and receipt idempotency, then cleans its network and
containers even after failure. Failure logs show container diagnostics. It checks
the HTML shell and HTTP boundaries; existing Playwright CI checks browser JS.
Private bind directories are created by the host runner before Compose startup;
otherwise Docker can create root-owned parents and prevent the host smoke from
writing its separate receipt. The first Linux CI run exposed this ownership gap
after all HTTP assertions passed; directory creation fixes the cause without
loosening permissions or changing the application checks.

On client date 2026-10-17, both script phases passed against a separately built
local instance on port 18081, including conflict rejection with no history append.
Recreated containers retained the full history and returned the original linked
outcome receipt. Temporary containers/network were removed afterward.
