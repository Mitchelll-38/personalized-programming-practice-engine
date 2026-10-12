# Personalized Programming Practice Engine

Programming knowledge-tracing research with an inspectable Java practice replay dashboard.

**Days 1–2 engineering implemented:** canonical causal data pipeline, strict CodeWorkout format adapter, audited CLI and versioned manifests, FastAPI + SQLite, and a React/TypeScript replay with supporting-history diagnostics. All committed data and demo outcomes are **synthetic**. The current predictor is an untrained, uncalibrated heuristic; no empirical ML results or learning gains are claimed. Day-two real-data acceptance remains blocked on verified access, terms and metadata.

[Two-week plan for three engineers](docs/sprint-plan.md) · [Day-one integration contract](docs/day-1-contract.md) · [Data access status](docs/data-access.md) · [Day-one delivery report](reports/day-1.md)

[Day-two delivery and individual PRs](reports/day-2.md) · [Browser replay smoke test](docs/browser-smoke.md)

Engineering workflow: [AGENTS.md](AGENTS.md) requires small, focused PRs, isolated agent worktrees, independent review and passing CI before rollout. All changes, including documentation and tests, follow this workflow.

## Run locally

Python 3.12+ and Node.js 22+ are required. Commands below are for PowerShell in the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd web
npm ci
npm run dev -- --host 127.0.0.1
```

Open **http://127.0.0.1:5173**. Select an exercise, inspect its statement and recommendation reasons, and record a simulated correct/incorrect outcome. The dashboard reloads history, estimates and rankings from the API. Outcomes persist across restarts. Retrying an exercise is recorded but does not inflate first-attempt evidence.

SQLite defaults to `.data/demo.sqlite3` (ignored by git). Override with `$env:PRACTICE_DB_PATH = 'C:\path\demo.sqlite3'` before starting the API. A fresh database seeds one synthetic learner. This is a local research demo: no authentication, trusted Java grading, code execution, or multi-user hosting. Public repository visibility does not mean the application has been deployed.

The Vite development server proxies `/api` to port 8000. A production static build needs an equivalent same-origin reverse proxy; day 1 does not include a hosted deployment.

## Research data pipeline

```powershell
.\.venv\Scripts\python.exe -m practice_engine.data.cli data/fixtures/synthetic.jsonl --output data/processed/day1 --seed 38 --synthetic --dataset-version synthetic-v1
```

Writes `audit.json`, `split.json`, and partitioned `train.jsonl`, `validation.jsonl`, `test.jsonl`. Each prediction example contains only earlier first attempts and the candidate's text/concepts; its label is stored separately. Retry events and ambiguous sequence positions cannot silently become extra primary targets. Seeded student grouping is independent of outcomes, and manifests include a source hash.

`manifest.json` records dataset, schema, feature and split versions plus content hashes of all five outputs. `--synthetic` is an explicit source declaration; absent it, provenance stays unverified. No trained model or verified redistribution terms are inferred. `practice_engine.data.manifest.verify_manifest(Path(...))` checks bundle integrity before reuse.

The default input is **canonical JSONL**. For the organizer-documented CodeWorkout format, use the separately supplied statement/concept catalog:

```powershell
.\.venv\Scripts\python.exe -m practice_engine.data.cli data/fixtures/codeworkout --format codeworkout --catalog data/fixtures/codeworkout/catalog.json --output data/processed/codeworkout-smoke --synthetic --dataset-version codeworkout-synthetic-v1
```

The adapter rejects missing grading/catalog fields, ambiguous timestamps and duplicate event/header keys. `audit.json` records event exclusions, label semantics and original table/catalog hashes; the processing manifest hashes the derived artifacts. This adapter is validated on original synthetic fixtures only. **Real release access, usage terms, grading semantics and catalog provenance remain unverified**; complete those gates before importing real data. No real student data is committed. Exercise-family splits and trained models remain later work.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd web
npm run build
```

CI runs the Python tests, synthetic data CLI, and frontend TypeScript/production build. Python dependencies are pinned in `requirements-dev.lock`; frontend dependencies in `web/package-lock.json`. `pyproject.toml` declares compatible installation ranges.

API docs: **http://127.0.0.1:8000/docs**. Endpoints: `/health`, `/exercises`, `/models/current`, `/students/demo/history`, `/students/demo/profile`, `/students/demo/recommendations`, `POST /predict`, and `POST /attempts`.

## Research direction

Predict first-attempt correctness on the next distinct exercise using strictly observed history and candidate content. Compare global/problem-rate, logistic regression, BKT, LSTM DKT, and a content-aware LSTM. Select and calibrate on validation only, then report held-out-student and held-out-exercise performance on locked tests. Concept output is **estimated performance**, not demonstrated mastery. Recommendation behavior is separate from evidence of improved learning.

The two-week sprint is a narrow full-time MVP plan for three engineers. Dataset access, usable metadata and compute determine whether empirical work completes within it; the original longer research scope remains follow-up work.
