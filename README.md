# Personalized Programming Practice Engine

Programming knowledge-tracing research with an inspectable Java practice replay dashboard.

The project includes a causal data pipeline, strict CodeWorkout format adapter,
versioned research artifacts/runs, FastAPI + SQLite, and a React replay dashboard.
Offline software supports rate/logistic/BKT models, CPU ID-only DKT training,
validation-only temperature scaling and frozen CodeBERT extraction. All committed
data and demo outcomes are **synthetic**. The active replay uses an untrained,
uncalibrated heuristic; an optional inspector queries fitted synthetic research
baselines separately. No real-data metrics or learning gains are claimed. The official full S19 archive is now privately acquired and checksum-verified;
[release acquisition](docs/release-acquisition.md) records terms and remaining
catalog, grading, ordering and real-source provenance gates.

[Two-week plan for three engineers](docs/sprint-plan.md) · [Day-one integration contract](docs/day-1-contract.md) · [Data access status](docs/data-access.md) · [Day-one delivery report](reports/day-1.md)

[Day-two delivery and individual PRs](reports/day-2.md) · [Browser replay smoke test](docs/browser-smoke.md)

[Chronological progress record](docs/progress.md) tracks implementation, decisions and review findings as work advances. The [research engineering status](reports/research-engineering-status.md) separates merged software from unmet experimental acceptance criteria across sprint work units.

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

[Synthetic replay walkthrough](docs/demo-walkthrough.md): inspect the policy, record an explicit choice, simulate outcomes and understand retry/persistence behavior.

## Research data pipeline

```powershell
.\.venv\Scripts\python.exe -m practice_engine.data.cli data/fixtures/synthetic.jsonl --output data/processed/day1 --seed 38 --synthetic --dataset-version synthetic-v1
```

Use a new output directory for every processing run; existing paths are rejected.
The complete bundle is published atomically after all artifacts and its manifest
are written; failed writes leave no partial output. See [processing bundles](docs/processing-bundles.md).

Writes `audit.json`, `split.json`, and partitioned `train.jsonl`, `validation.jsonl`, `test.jsonl`. Each prediction example contains only earlier first attempts and the candidate's text/concepts; its label is stored separately. Retry events and ambiguous sequence positions cannot silently become extra primary targets. Seeded student grouping is independent of outcomes, and manifests include a source hash.

`manifest.json` records dataset, schema, feature and split versions plus content hashes of all five outputs. `--synthetic` is an explicit source declaration; absent it, provenance stays unverified. No trained model or verified redistribution terms are inferred. `practice_engine.data.manifest.verify_manifest(Path(...))` checks bundle integrity before reuse.

The default input is **canonical JSONL**. For the organizer-documented CodeWorkout format, use the separately supplied statement/concept catalog:

```powershell
.\.venv\Scripts\python.exe -m practice_engine.data.cli data/fixtures/codeworkout --format codeworkout --catalog data/fixtures/codeworkout/catalog.json --output data/processed/codeworkout-smoke --synthetic --dataset-version codeworkout-synthetic-v1
```

The adapter rejects missing grading/catalog fields, ambiguous timestamps and duplicate event/header keys. `audit.json` records event exclusions, label semantics and original table/catalog hashes; the processing manifest hashes the derived artifacts. This adapter is validated on original synthetic fixtures only. **The official S19 archive is privately acquired; catalog, grading/order interpretation and reviewed real-source provenance remain import gates**. Current terms restrict use to noncommercial research and prohibit redistribution; see the [acquisition record](docs/release-acquisition.md). No real student data is committed. Exercise-family splits and synthetic fitted models are implemented separately; their existence does not validate this release's grading, chronology or catalog.

## Optional research workflows

For a built frontend and API in one local command, see the
[Docker Compose demo instructions](docs/local-containers.md).

Keep private data, model weights and encoder caches under ignored project storage.
These opt-in workflows are separate from the heuristic replay:

- [Student/family baseline runs](docs/baseline-training.md) and [CPU DKT training](docs/dkt-training.md).
- [Validation calibration runs](docs/calibration-runs.md) and [research API configuration](docs/research-api.md).
- [Research inspector](docs/research-inspector.md), including explicit scalar-fitting limitations.
- [Optional encoder setup](docs/encoder-environment.md) and [frozen extraction](docs/codebert-extraction.md).
- [Recommendation generation records](docs/recommendation-records.md); generation is not proof of display or choice.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd web
npm run build
```

CI runs the Python tests, synthetic data CLI, and frontend TypeScript/production build. Python dependencies are pinned in `requirements-dev.lock`; frontend dependencies in `web/package-lock.json`. `pyproject.toml` declares compatible installation ranges.

Baseline research dependencies are pinned in `requirements-research.lock`, included by the development lockfile so the complete test suite is reproducible. A runtime-only `pip install .` keeps the demo API lightweight; `pip install '.[research]'` enables NumPy/scikit-learn separately. New research subpackages are discovered automatically during packaging.

API docs: **http://127.0.0.1:8000/docs**. Endpoints: `/health`, `/exercises`, `/models/current`, `/students/demo/history`, `/students/demo/profile`, `/students/demo/recommendations`, `POST /predict`, and `POST /attempts`.

## Research direction

Predict first-attempt correctness on the next distinct exercise using strictly observed history and candidate content. Compare global/problem-rate, logistic regression, BKT, LSTM DKT, and a content-aware LSTM. Select and calibrate on validation only, then report held-out-student and held-out-exercise performance on locked tests. Concept output is **estimated performance**, not demonstrated mastery. Recommendation behavior is separate from evidence of improved learning.

The two-week sprint is a narrow full-time MVP plan for three engineers. Dataset access, usable metadata and compute determine whether empirical work completes within it; the original longer research scope remains follow-up work.
