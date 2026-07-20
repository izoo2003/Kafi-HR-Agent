# HR & Admin Agent

Phase 1: **CV Ranking** — ingests candidate CVs from Gmail and a Google
Form, scores them against role-specific criteria using Gemini, ranks them
per position, and produces HR-friendly formatted Excel reports. A React
dashboard lets HR trigger the pipeline and browse rankings without touching
the CLI.

WhatsApp intake is stubbed for a later phase.

## Structure

```
backend/    Python — FastAPI + CLI, ingestion/scoring/ranking/reporting pipeline
frontend/   React + Vite + TypeScript — admin dashboard consuming the backend API
```

See `backend/README.md` and `frontend/README.md` for full setup details
(Gemini API key, Google OAuth, Google Form field spec, etc.). Quick start
below assumes that one-time setup is already done.

## Running the project

Two terminals, from the project root:

**Terminal 1 — backend API** (port **8808**)

```powershell
cd backend
.venv\Scripts\activate
python main.py
```

**Terminal 2 — frontend dashboard** (port **5288**)

```powershell
cd frontend
npm run dev
```

Then open http://localhost:5288 (or http://127.0.0.1:5288).

### Alternative: backend-only via CLI (no dashboard, scriptable/cron-friendly)

```powershell
cd backend
.venv\Scripts\activate
python main.py cli run-all
```

## Multi-agent integration

This agent is built to plug into a future shared orchestrator without a
rewrite — see the always-applied Cursor rule `.cursor/rules/hr-admin-agent.mdc`
and `backend/app/integration/interface.py`, the only module a parent/sibling
agent should ever import from.
