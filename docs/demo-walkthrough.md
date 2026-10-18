# Synthetic replay walkthrough

Owner: product engineer. Purpose: help a new user distinguish inspecting an
exercise, explicitly choosing a recommendation and recording simulated correctness.
Acceptance: current labels; a clean synthetic replay checked against real browser
flows; accurate retry/linkage and private persistence behavior; honest model/data
gates. Dependencies: container recipe #63 (merged) and policy disclosure #62
(required before this guide merges). No application behavior changes.

## Start a separate local demo

Follow the [container setup](local-containers.md). For a walkthrough that preserves
an existing demo, use a new project-contained data directory and another loopback
port. From the repository root in PowerShell with Docker running:

```powershell
$env:PRACTICE_DEMO_DATA_DIR = Join-Path (Get-Location) '.data/private/data/walkthrough-01'
$env:PRACTICE_DEMO_PORT = '8081'
New-Item -ItemType Directory -Force -Path $env:PRACTICE_DEMO_DATA_DIR | Out-Null
docker compose -p practice-engine-walkthrough -f deploy/compose.yaml up --build -d --wait
```

Create the bind directory as your host user before Compose starts, especially on
Linux where Docker may otherwise create root-owned parent directories. The API
still owns its container-written SQLite file; no broad permission changes are
needed.

Open **http://127.0.0.1:8081**. A new database seeds a synthetic learner. If this
directory already contains a database, its previous outcomes remain; choose a new
directory name for a fresh rehearsal. Do not share the same data directory between
running instances. Keep these local files out of public Git.

The dashboard says **Synthetic research demo**. The active replay uses an
untrained, uncalibrated heuristic. It does not execute Java or grade submissions;
you choose the simulated outcome yourself.

## Inspect, choose, then simulate

1. Use **Exercise library** to select **Reverse a string**, or click its
   recommendation. Inspect the prompt and reasons. Default selection, browsing and
   inspection do not record a recommendation choice or correctness.
2. In **Configured heuristic policy**, read the estimated-correctness challenge
   band. The default is 60.0-80.0%; configured servers can use another range.
   Expand **Inspect policy configuration** for the exact declared parameters and
   hash. The band is a hypothesis with no measured learning benefit; the hash
   identifies declared configuration and does not authenticate results.
3. Click **Choose this recommendation**. Wait for **Choice recorded** and the
   notice that the next simulated outcome will link to your recorded choice.
   Choosing alone leaves **Recent history** and **Concept estimates** unchanged.
4. Click **Simulate incorrect**. Wait for the saved-interaction message and
   refreshed history. One interaction is added and linked to the acknowledged
   choice. **Recent history** shows the exercise, attempt number and outcome.
   For a new exercise, its first attempt contributes to estimated performance.
   Expand **Inspect supporting first attempts** in the relevant concept to inspect
   the supporting exercise/outcome; this evidence is not proven mastery.
5. With the same exercise selected, click **Simulate correct** to rehearse a retry.
   This is a new simulated interaction, not a resend of the prior request. The
   retry appears in history but does not replace first-attempt evidence or inflate
   its distinct-exercise support. The prior choice acknowledgement was cleared
   after success; this new simulation is unlinked unless you choose again.

You can simulate without choosing. You can also simulate while a choice request
is still pending; that outcome remains unlinked. Only an acknowledgement already
received at the outcome click can link to it. Changing exercise or refreshing the
workspace clears the acknowledgement; links are never attached retroactively.

If a linked outcome request fails ambiguously, the acknowledgement is retained.
Retrying the same choice/exercise/correctness returns its original stored receipt
without appending another interaction. A contradictory outcome is rejected.
Errors are displayed; the UI never silently resends a failed linked outcome as
unlinked. A failed *choice* request has different semantics: **Retry choice** can
create another choice event, as the displayed warning explains.

## Optional fitted-model inspection

Before simulating a new exercise, click **Inspect fitted baseline**. With the
standard container setup, expect **No fitted baseline configured. The demo remains
available.** An exercise already in history instead explains that a first-attempt
model requires a new exercise; demo retries are still available.

A separately configured local research server can display a fitted synthetic
estimate with model/dataset versions. **Synthetic fitted estimate** is explicitly
uncalibrated. **Temperature-scaled synthetic estimate** applies a fitted scalar;
its fitting record does not establish independently measured reliability. Neither
mode changes replay rankings or concept estimates. See the [research inspector](research-inspector.md)
and [research API configuration](research-api.md). The standard container recipe
does not activate models or download research weights.

## Stop, resume and reset context

Reload the page or stop and start the same Compose project to see persisted
history. Page reload clears transient choice acknowledgement, not stored events.

```powershell
docker compose -p practice-engine-walkthrough -f deploy/compose.yaml down
```

This removes containers/network and preserves the private database. To rehearse a
fresh learner, choose a new private directory before starting again; deleting
containers alone does not reset history. Keep the same port/data environment when
resuming this walkthrough. The [local container guide](local-containers.md)
describes overrides and persistence in more detail.

All examples are software demonstrations on synthetic records. Real CodeWorkout
release access, usage terms, catalog/grading verification and real-data evaluation
remain open gates. There is no locked-test report or measured learning gain.
