# Kafi HR & Admin Agent

Internal HR system for **Kafi Commodities**: people, hiring, attendance, payroll, KPI, policy, and employee development in one admin app.

Specs live in `docs/` and are mirrored as Cursor rules under `.cursor/rules/`.

**Live**

| Layer | URL |
|-------|-----|
| Frontend (Vercel) | https://kafi-admin-hr-agent.vercel.app |
| API (Railway) | https://kafi-hr-agent-production.up.railway.app |
| OpenAPI | https://kafi-hr-agent-production.up.railway.app/docs |
| Health | https://kafi-hr-agent-production.up.railway.app/api/v1/integration/health |

> Do **not** use the old API host `kafi-hr-agent.up.railway.app` — it is stale. Frontend `VITE_API_BASE_URL` must be `https://kafi-hr-agent-production.up.railway.app/api/v1`.

**Source (twin remotes — push both)**

| Remote | Repo |
|--------|------|
| `origin` | https://github.com/izoo2003/Kafi-HR-Agent |
| `kafi` | https://github.com/kafi-group/Kafi-Admin-HR-Agent |

```powershell
git push origin HEAD
git push kafi HEAD
```

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Alembic, JWT + RBAC |
| Database | **Supabase Postgres** (primary); local SQLite fallback for offline/dev |
| Files | **Supabase Storage** (`employee-documents` bucket) for CVs, CNIC, employee/referral docs |
| Frontend | React 18, Vite, TypeScript, React Query, React Router |
| Deploy | Railway (`backend/`), Vercel (`frontend/`) |

---

## What’s in the app

| Section | What you can do |
|---------|-----------------|
| **Auth** | Sign in with email or username, plus PIN or password. HR creates accounts and links them to employee records. |
| **Admin** | Operational dashboard (headcount, open roles, pending items) with status-colored tiles. |
| **My role** | Department job description and SOPs for the signed-in employee’s role. |
| **Employees** | Profiles, bank/salary, documents, referrals. **Departments** include JD + SOPs (type, AI generate, or attach PDF/image). Appointment and contract letters. CNIC and education checks. Files → Supabase Storage. |
| **Job Postings** | Create/edit roles, AI draft, Google Form apply link, hiring poster (`hr@kafi-group.com`), optional LinkedIn post. |
| **CV Screening** | Sync CVs from IMAP + Google Form (Outlook / Gmail / WhatsApp optional). Parse, score, rank, shortlist, hire. |
| **Attendance** | Daily records, leave requests, WebHR/period reports. Feeds payroll. |
| **Payroll** | Salary sheets (tax on base, IBFT/Cheque/Cash counts), advances, run lifecycle (`draft` → `pending_approval` → `approved` → `paid`). |
| **KPI** | Department definitions, actuals, employee/department rollups. |
| **Employee Development** | Performance, training, things to learn. **Resignation:** draft/send letter; HR accept/reject or issue letters. |
| **HR Policies** | Editable company handbook. Copy-all. Visible to every signed-in user. |
| **User Management** | Users, roles, access matrix, audit log, system config. |

Employee self-service accounts see **My role**, **Attendance**, **KPI**, **Employee Development** (including resignation), and **HR Policies** — scoped to their own records.

---

## Implementation status

| Phase | Module | Status |
|-------|--------|--------|
| 0 | Foundation (auth, RBAC, shell) | Done |
| 1 | Employees & departments | Done |
| 2 | CV screening / job descriptions | Done (core) |
| 3 | Attendance | Done |
| 4 | Payroll | In progress / partial (salary sheets + tax live) |
| 5 | KPI | Specced; follow `docs/FEATURE_KPI.md` |
| 6 | Admin panel & audit UI | Partial (dashboard / users exist; full panel per docs) |
| 7 | Integration hardening | Not started |

Build order: see `docs/IMPLEMENTATION_PHASES.md` and `.cursor/rules/phases-implementation.mdc`.

---

## Structure

```
backend/    FastAPI `/api/v1`, JWT + RBAC, SQLAlchemy, Alembic, Supabase Storage helpers
frontend/   React 18 + Vite + TypeScript, React Query
docs/       Specs (schema, API, features, integration contract)
.cursor/rules/  Always-on AI guidance (incl. twin remotes)
```

---

## Running locally

**Terminal 1 — backend**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Fill DATABASE_URL + SUPABASE_* (see below), then:
python main.py
```

API defaults to http://127.0.0.1:8808 (or `API_PORT` from `.env`) — docs: `/docs`.

Restart the API after Python changes (`python main.py` does not auto-reload unless `API_RELOAD=1`).

**Terminal 2 — frontend**

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:5288. Seed admin (from `backend/.env`): `admin@kafi-group.com` / `Admin123`.

### Required Supabase env (backend)

```env
DATABASE_URL=postgresql+psycopg2://postgres.PROJECT_REF:%40YOUR_PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres?sslmode=require
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...
SUPABASE_JWKS_URL=https://PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_PROJECT_REF=PROJECT_REF
SUPABASE_STORAGE_BUCKET=employee-documents
```

If the DB password contains `@`, URL-encode it as `%40` in `DATABASE_URL`.

Local SQLite fallback (optional): `DATABASE_URL=sqlite:///data/hr_agent_v2.db`.

---

## Deploy notes

- **Railway (backend):** set `DATABASE_URL`, all `SUPABASE_*`, JWT, Gemini, IMAP/Google Form, `CORS_ORIGINS` / `CORS_ORIGIN_REGEX`, `PUBLIC_API_URL=https://kafi-hr-agent-production.up.railway.app`. After env changes, redeploy and confirm health `db_connected: true`.
- **Vercel (frontend):** root directory `frontend`. Set `VITE_API_BASE_URL=https://kafi-hr-agent-production.up.railway.app/api/v1` (also in `frontend/vercel.json`). Redeploy after changing this — Vite bakes it in at build time.
- **CORS:** allow `https://kafi-admin-hr-agent.vercel.app` and/or `CORS_ORIGIN_REGEX=https://.*\.vercel\.app`.
- Never commit `backend/.env`, `frontend/.env`, or `backend/credentials/*.json`.
- Do not commit runtime files under `backend/data/` (IMAP UIDs, Google Form state).

---

## Docs

| Pack | Files |
|------|--------|
| Foundational | `docs/PROJECT_OVERVIEW.md`, `DATABASE_SCHEMA.md`, `API_ENDPOINTS.md`, `INTEGRATION_CONTRACT.md` |
| Backend | `docs/BACKEND_ARCHITECTURE.md`, `AUTH_AND_RBAC.md` |
| Frontend | `docs/FRONTEND_ARCHITECTURE.md`, `UI_DESIGN_SYSTEM.md` |
| Features | `FEATURE_CV_SCREENING.md`, `FEATURE_ATTENDANCE.md`, `FEATURE_PAYROLL.md`, `FEATURE_KPI.md`, `FEATURE_ADMIN_PANEL.md`, `FEATURE_AUDIT_LOG.md` |
| Build order | `docs/IMPLEMENTATION_PHASES.md` |
| Git | `.cursor/rules/git-twin-remotes.mdc` |
