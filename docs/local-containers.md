# Local container replay

Owner: coordinator. Purpose: start the existing synthetic replay with one local
Compose command and a built static frontend/API proxy. Dependencies: existing
React build and FastAPI/SQLite contracts. Acceptance: pinned runtime/base inputs;
private data/context excluded from images; health-gated API startup; loopback-only
published port; persistent project-contained SQLite; actual choice/attempt/retry
behavior through the proxy. No hosted publication or neural runtime is bundled.

Plan before implementation: two small images (locked Python runtime; Node build
stage copied into Nginx), internal API service, same-origin /api proxy and ignored
bind-mounted data under the project. Verify compose configuration, image build,
private-context exclusion, HTTP replay and restart persistence. CI automation for
this recipe follows as a separate focused change.

## Start and stop

With Docker Engine and the Compose plugin running, execute from the repository
root (PowerShell, bash or a compatible terminal):

```text
docker compose -f deploy/compose.yaml up --build -d --wait
```

Open http://127.0.0.1:8080. The static web server forwards `/api/` to the internal
API; the API publishes no host port. Only loopback receives the web port. This
is a single-user local synthetic demo without authentication or Java execution.
API documentation is at http://127.0.0.1:8080/api/docs; the container's `/api`
root path makes its OpenAPI request use the same proxy.

```text
docker compose -f deploy/compose.yaml down
```

Stopping/removing containers preserves the bind-mounted SQLite directory at
`.data/private/data/container-demo/` under this checkout. Treat its contents as
local data; do not commit it. `PRACTICE_DEMO_PORT` can select another host port.
`PRACTICE_DEMO_DATA_DIR` can select another absolute project-contained directory;
relative overrides resolve against `deploy/`, not the current shell directory.
Use a separate directory and Compose project name for isolated checks. Do not
point multiple running instances at the same SQLite file.

## Build and runtime boundaries

The API installs the runtime-only `requirements-runtime.lock`; optional research,
Torch, encoder downloads and model activation are absent. Base images are pinned
by registry digest. The frontend installs `web/package-lock.json` in a Node build
stage and copies only its compiled output into Nginx. This follows Docker's
[multi-stage build mechanism](https://docs.docker.com/build/building/multi-stage/).
Compose waits for API health before starting the web service using
[`service_healthy`](https://docs.docker.com/compose/how-tos/startup-order/).

`.dockerignore` excludes private storage, Git/worktrees, local environments,
generated outputs and SQLite files from the build context. Dockerfiles explicitly
copy application source and dependency inputs. No dataset or model is embedded.
Updating dependencies requires updating the appropriate lockfile and checking
both builds again. Digest pins make inputs explicit; they need ongoing updates.

## Verification record

On client date 2026-10-17, Docker Desktop Engine 29.4.2 / Compose 5.1.3 built both
images, including `pip check`, TypeScript and the production web build. A separate
project on loopback port 18080 with its own private synthetic database passed:
static HTML and proxied health, recommendation generation, explicit choice,
linked simulated outcome, identical retry without another history row, and API
restart retaining all six synthetic history rows. A clean API image inspection
found no private directory, SQLite files, Git, worktrees or installed Torch.
The temporary containers/network were removed; the private test database remains
under the contained worktree. These are local runtime checks, not hosted rollout
or predictive-quality evidence. Container-specific CI is a separate follow-up.
