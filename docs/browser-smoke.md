# Browser replay smoke test

Install the Python development dependencies as in the README, then run from `web/`:

```powershell
npm ci
npx playwright install chromium
$env:PRACTICE_TEST_PYTHON = (Resolve-Path ../.venv/Scripts/python.exe).Path
npm run test:e2e
```

On Linux/macOS, activate the project virtual environment and run the same npm
commands; `python` is the default interpreter. `PRACTICE_TEST_PYTHON` can select
another installed interpreter with the project's Python dependencies.

The suite owns loopback ports 8001 and 5174 and refuses existing servers. It uses
a unique system temporary SQLite database with synthetic seed history, never the
developer's replay database. Normal API shutdown cleans up the temporary directory;
forced process termination can leave a temporary directory for OS cleanup.
Vite's optional `PRACTICE_API_URL` proxy override points this test at port 8001;
normal development still defaults to port 8000.

The Chromium test exercises the actual React/API replay: neutral-prior disclosure,
first-attempt evidence, retry exclusion, supporting outcomes and reload persistence.
CI runs it separately from unit/build checks and uploads traces on failure. This
smoke does not cover every browser, accessibility requirement or deployment mode.
