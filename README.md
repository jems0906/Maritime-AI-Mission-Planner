# Maritime AI Mission Planner

Decision-support web application for synthetic maritime search missions.

## Safety and governance stance

This tool provides AI recommendations only. It does **not** autonomously task assets or finalize search actions. Every recommendation must be accepted, rejected, or overridden by a human reviewer with a written justification.

## What it does

- Generates or uploads synthetic mission grid data.
- Ranks sectors by anomaly likelihood and incomplete coverage risk.
- Visualizes recommendations in an interactive map/grid with explainability details.
- Enforces human-in-the-loop review and stores decisions in an audit history.
- Produces an after-action report with coverage, review outcomes, model metrics, and improvement suggestions.

## Stack

- Frontend: React + TypeScript + Leaflet
- Backend: FastAPI + SQLAlchemy
- ML: scikit-learn logistic ranking model persisted with joblib
- Database: PostgreSQL (Railway-ready), local SQLite fallback

## Project layout

- `backend/` FastAPI API, ML ranking logic, data model, audit workflow
- `frontend/` React UI and Leaflet grid
- `sample_data/` Uploadable mission JSON and CSV examples
- `docker-compose.yml` Local full-stack orchestration with PostgreSQL

## Backend setup (local)

1. `cd backend`
2. Use Python 3.12 for best compatibility with prebuilt scientific wheels.
3. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. Set env vars (or copy from `.env.example`):
   - `DATABASE_URL` (default local SQLite if omitted)
   - `MODEL_PATH`
   - `CORS_ORIGINS`
   - Optional role keys for protected operations:
     - `OPERATOR_API_KEY`
     - `REVIEWER_API_KEY`
     - `ADMIN_API_KEY`
6. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Database migrations (Alembic)

- Initial migration is included at `backend/alembic/versions/0001_initial_schema.py`.
- Run migrations:
   - `cd backend`
   - `alembic -c alembic.ini upgrade head`
- Create a new migration after model changes:
   - `alembic -c alembic.ini revision --autogenerate -m "describe_change"`

For migration-first environments (recommended on Railway PostgreSQL), set `AUTO_CREATE_SCHEMA=false` and run Alembic during deployment/release.

If your local DB was previously created via SQLAlchemy startup auto-create and already has tables, baseline it first:

- `alembic -c alembic.ini stamp head`

Then future model changes should use migration revisions and `upgrade head`.

## Frontend setup (local)

1. `cd frontend`
2. `npm install`
3. Create `.env` from `.env.example` (optional if backend is at localhost:8000)
    - Optional UI-side role keys:
       - `VITE_OPERATOR_API_KEY`
       - `VITE_REVIEWER_API_KEY`
       - `VITE_ADMIN_API_KEY`
4. `npm run dev`

If your host blocks native Node binaries such as esbuild/rollup, the default `npm run dev` starts a fallback static runtime with API proxy support.

- Fallback runtime: `npm run dev`
- Vite React runtime (when native binaries are available): `npm run dev:vite`

The UI shows a runtime banner so you can quickly confirm which mode is active.

## One-command local launcher (Windows)

Run both backend and frontend in separate PowerShell windows:

1. `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1`

Preview commands without launching:

1. `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1 -DryRun`

This starts:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

Stop both launched terminals:

1. `powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1`

Preview stop targets without killing processes:

1. `powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1 -DryRun`

## Quick start with Docker

1. `docker compose up --build`
2. Frontend: `http://localhost:5173`
3. Backend OpenAPI: `http://localhost:8000/docs`

## Typical flow

1. Generate a synthetic scenario or upload `sample_data/mission_upload_example.json` or `sample_data/mission_upload_example.csv`.
2. Optionally train the model with current synthetic data.
3. Rank sectors to produce AI recommendations.
4. Human reviewer records accept/reject/override and justification per recommendation.
5. Review after-action report metrics and suggested improvements.

## Railway deployment notes

Create three Railway services:

1. PostgreSQL service.
2. Backend service:
   - Root: `backend/`
   - Build: Dockerfile
   - Variables:
     - `DATABASE_URL` from Railway Postgres connection string in SQLAlchemy format: `postgresql+psycopg://...`
     - `CORS_ORIGINS` set to frontend Railway URL
     - `MODEL_PATH=ml_artifacts/ranker.joblib`
   - `AUTO_CREATE_SCHEMA=false`
3. Frontend service:
   - Root: `frontend/`
   - Build: Dockerfile
   - Variable:
     - `VITE_API_BASE_URL=https://<backend-service-domain>/api`

## API highlights

- `POST /api/scenarios/generate`
- `POST /api/scenarios/upload`
- `POST /api/scenarios/upload-csv`
- `POST /api/scenarios/{id}/rank`
- `POST /api/recommendations/{id}/review`
- `GET /api/scenarios/{id}/report`
- `GET /api/scenarios/{id}/report.md`
- `GET /api/scenarios/{id}/audit`
- `GET /api/users`
- `POST /api/admin/train`

Protected routes (`generate/upload/rank/review/train`) enforce API keys only when corresponding backend key env vars are configured.

## Backend tests

- `cd backend`
- `python -m pip install -r requirements.txt`
- `pytest -q`

CI is configured in `.github/workflows/backend-tests.yml` to run backend tests on push and pull request changes under `backend/`.

## Interview-ready framing

"I built this as a recommendation and prioritization aid, not an automation engine. The system surfaces explainable, confidence-scored search priorities, but a human operator must approve every final tasking decision."
