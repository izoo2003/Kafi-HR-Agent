# HR & Admin Agent

Bounded HR & Admin capability module (Agent 10). Specs live in `docs/` and
are mirrored as always-on Cursor rules under `.cursor/rules/`.

## Structure

```
backend/    Python FastAPI — /api/v1, JWT auth, SQLAlchemy, Alembic
frontend/   React + Vite + TypeScript (awaiting frontend rule pack)
docs/       Foundational + backend architecture sources of truth
```

## Running

**Terminal 1 — backend (port 8808)**

```powershell
cd backend
.venv\Scripts\activate
python main.py
```

**Terminal 2 — frontend (port 5288)**

```powershell
cd frontend
npm run dev
```

Open http://localhost:5288 — sign in with seed admin from `backend/.env`
(default `admin@kafi-group.com` / `ChangeMeAdmin123!`).

## Docs / rules

| Pack | Docs |
|------|------|
| Foundational | `PROJECT_OVERVIEW`, `DATABASE_SCHEMA`, `API_ENDPOINTS`, `INTEGRATION_CONTRACT` |
| Backend | `BACKEND_ARCHITECTURE`, `AUTH_AND_RBAC` |
| Frontend | `FRONTEND_ARCHITECTURE`, `UI_DESIGN_SYSTEM` |
| Next | Feature packs + `IMPLEMENTATION_PHASES.md` |
