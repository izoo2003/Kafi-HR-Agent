# Kafi HR & Admin Agent

Internal HR system for **Kafi Commodities**: people, hiring, attendance, payroll, KPI, policy, and employee development in one admin app.

Specs live in `docs/` and are mirrored as Cursor rules under `.cursor/rules/`.

**Live**

| Layer | URL |
|-------|-----|
| Frontend (Vercel) | https://kafi-hr-agent.vercel.app |
| API (Railway) | https://kafi-hr-agent.up.railway.app |
| OpenAPI | https://kafi-hr-agent.up.railway.app/docs |

**Source**

- Personal: https://github.com/izoo2003/Kafi-HR-Agent
- Org: https://github.com/kafi-group/Kafi-Admin-HR-Agent

---

## What’s in the app

| Section | What you can do |
|---------|-----------------|
| **Auth** | Sign in with email or username, plus PIN or password. Staff can still use email. HR creates accounts and links them to employee records. |
| **Admin** | Operational dashboard (headcount, open roles, pending items) with status-colored tiles. |
| **My role** | Department job description and SOPs for the signed-in employee’s role. |
| **Employees** | Profiles, bank/salary, documents, referrals. **Departments** include a Job Description (JD) and SOPs — type, generate with AI, or attach PDF/image. Appointment and contract letters. CNIC and education document checks. Files go to Supabase Storage. |
| **Job Postings** | Create/edit roles, AI draft of description/requirements, Google Form apply link in the posting text, hiring poster (apply via `hr@kafi-group.com` on the image), optional LinkedIn post. |
| **CV Screening** | Sync CVs from webmail IMAP and Google Form (Outlook / Gmail / WhatsApp optional). Parse, score, rank, shortlist, hire. |
| **Attendance** | Daily records, leave requests, period reports. Feeds payroll. |
| **Payroll** | Salary sheets, tax slabs, compute, advances, run lifecycle (draft → approved → paid). |
| **KPI** | Department definitions, actuals, employee/department rollups. |
| **Employee Development** | Performance, training, things to learn. **Resignation:** employee drafts/sends a letter; HR accepts or rejects. HR can also issue letters. |
| **HR Policies** | Editable company handbook (documents, timings, SOP, leave, confidentiality). Copy-all for the full text. Visible to every signed-in user. |
| **User Management** | Users, roles, access matrix, audit log, system config. |

Employee self-service accounts see **My role**, **Attendance**, **KPI**, **Employee Development** (including resignation), and **HR Policies** — scoped to their own records.

---

## Structure

```
backend/    FastAPI `/api/v1`, JWT + RBAC, SQLAlchemy, Alembic
frontend/   React 18 + Vite + TypeScript, React Query
docs/       Specs (schema, API, features, integration contract)
```

---

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

Restart the API after Python changes (`python main.py` does not auto-reload unless `API_RELOAD=1`).

**Terminal 2 — frontend (port 5288)**

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:5288. Seed admin is in `backend/.env` (default `admin@kafi-group.com` / `Admin123`).

---

## Deploy notes

- **Railway:** `backend/` — `DATABASE_URL` (Supabase Postgres), JWT, Gemini, IMAP/Google Form, `CORS_ORIGINS` / `CORS_ORIGIN_REGEX`.
- **Vercel:** root directory `frontend` — production API base `https://kafi-hr-agent.up.railway.app/api/v1`.
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
