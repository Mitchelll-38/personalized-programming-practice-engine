# Research workspace

Day 1 React / TypeScript dashboard for the local synthetic demo. Requires Node.js 20.19+ or 22+ and the FastAPI server on `http://127.0.0.1:8000`.

```sh
cd web
npm ci
npm run dev
```

Open the URL printed by Vite. Requests to `/api` are proxied to FastAPI with the prefix removed. Start the backend separately from the repository root using `uvicorn api.main:app --reload` in the project's Python environment.

```sh
npm run build
```

The workspace loads exercise prompts, a concept profile, recommendations, model metadata, and recent interaction history. Recording a simulated correct or incorrect outcome refreshes the profile, ranking, and history. If a save succeeds but the refresh fails, replay buttons stay disabled until a successful refresh to prevent an accidental duplicate.

All outcomes are simulated. Estimates are untrained and uncalibrated. This prototype does not execute Java or grade submitted code. The Vite proxy is for local development; a production deployment needs an explicitly configured API route.
