# Kafi HR & Admin Agent

Internal HR system for Kafi Commodities: people, hiring, attendance, payroll, KPI, and company policy in one admin app. Specs live in `docs/` and are mirrored as Cursor rules under `.cursor/rules/`.

**Live:** frontend on Vercel, API on Railway (`https://kafi-hr-agent.up.railway.app`).

## What’s in the app

| Section | What you can do |
|---------|-----------------|
| **Auth** | Login with email or username. Employees can self-register; HR links accounts to employee records. |
| **Employees** | Profiles, departments, documents, referrals, CNIC image verify. Files go to Supabase Storage. |
| **Job Postings** | Create/edit roles, AI draft of description/requirements, Google Form apply link, optional LinkedIn post. |
| **CV Screening** | Sync CVs from webmail IMAP and Google Form (Outlook / Gmail / WhatsApp optional). Parse, score, rank, shortlist. |
| **Attendance** | Daily records, leave requests, period reports. Feeds payroll. |
| **Payroll** | Salary sheets, tax slabs, compute, advances, run lifecycle (draft → approved → paid). |
| **KPI** | Department definitions, actuals, employee/department rollups, personal KPIs for self-service users. |
| **HR Policies** | KAFI handbook (documents, timings, SOP, leave, confidentiality). **Copy all** puts the full text on the clipboard. Visible to every signed-in user, including employees. |
| **Admin / Users** | Dashboard, user list, audit log, system config. |

Employee self-service accounts only see Attendance, KPI, and HR Policies for their own records.

## Structure

```
backend/    FastAPI `/api/v1`, JWT + RBAC, SQLAlchemy, Alembic
frontend/   React 18 + Vite + TypeScript, React Query
docs/       Specs (schema, API, features, integration contract)
```

## Running locally

**Terminal 1 — backend (port 8808)**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

API: http://127.0.0.1:8808 — docs: http://127.0.0.1:8808/docs

Restart the API after code changes (`python main.py` does not auto-reload unless `API_RELOAD=1`).

**Terminal 2 — frontend (port 5288)**

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:5288. Seed admin is in `backend/.env` (default `admin@kafi-group.com` / `ChangeMeAdmin123!`).

## Deploy notes

- **Railway:** `backend/` — `DATABASE_URL` (Supabase Postgres), JWT, Gemini, IMAP/Google Form, `CORS_ORIGINS` / `CORS_ORIGIN_REGEX`.
- **Vercel:** root directory `frontend` — production API base `https://kafi-hr-agent.up.railway.app/api/v1`.
- Never commit `backend/.env`, `frontend/.env`, or `backend/credentials/*.json`.

## Docs

| Pack | Files |
|------|--------|
| Foundational | `docs/PROJECT_OVERVIEW.md`, `DATABASE_SCHEMA.md`, `API_ENDPOINTS.md`, `INTEGRATION_CONTRACT.md` |
| Backend | `docs/BACKEND_ARCHITECTURE.md`, `AUTH_AND_RBAC.md` |
| Frontend | `docs/FRONTEND_ARCHITECTURE.md`, `UI_DESIGN_SYSTEM.md` |
| Features | `FEATURE_CV_SCREENING.md`, `FEATURE_ATTENDANCE.md`, `FEATURE_PAYROLL.md`, `FEATURE_KPI.md`, `FEATURE_ADMIN_PANEL.md`, `FEATURE_AUDIT_LOG.md` |
| Build order | `docs/IMPLEMENTATION_PHASES.md` |
