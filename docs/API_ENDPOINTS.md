# API ENDPOINTS — HR & Admin Agent

> All routes prefixed with `/api/v1`. All routes (except `/auth/login`) require a valid JWT bearer token. All routes are additionally gated by the RBAC permission matrix — see `AUTH_AND_RBAC.md`. Request/response bodies are Pydantic models defined under `backend/app/schemas/`; frontend TS types under `frontend/src/types/` must mirror them exactly.

**Conventions:**
- Standard REST verbs: `GET` (read), `POST` (create), `PATCH` (partial update), `DELETE` (soft-delete where applicable).
- List endpoints support `?page=&page_size=&sort=&filter[...]=` query params.
- All list responses shaped as `{ items: [...], total: int, page: int, page_size: int }`.
- All error responses shaped as `{ error: { code: string, message: string, details?: object } }` with appropriate HTTP status.
- Every write endpoint (`POST`/`PATCH`/`DELETE`) automatically emits an audit log entry — see `FEATURE_AUDIT_LOG.md`.

---

## 1. Auth

| Method | Path | Purpose | Auth |
|---|---|---|---|
| POST | `/auth/login` | Email+password login, returns JWT | none |
| POST | `/auth/logout` | Invalidate session/token | required |
| POST | `/auth/refresh` | Refresh access token | required (refresh token) |
| GET | `/auth/me` | Current user profile + roles + permissions | required |

---

## 2. Users & Roles (Admin Panel)

| Method | Path | Purpose |
|---|---|---|
| GET | `/users` | List users (paginated, filterable by role/status) |
| POST | `/users` | Create user |
| GET | `/users/{id}` | Get user detail |
| PATCH | `/users/{id}` | Update user (name, active status) |
| DELETE | `/users/{id}` | Deactivate user (soft delete) |
| GET | `/roles` | List all roles |
| POST | `/roles` | Create role |
| PATCH | `/roles/{id}` | Update role |
| GET | `/users/{id}/roles` | Get roles assigned to a user |
| POST | `/users/{id}/roles` | Assign role to user |
| DELETE | `/users/{id}/roles/{role_id}` | Remove role from user |
| GET | `/access-matrix` | Get full agent/module/role access matrix |
| PATCH | `/access-matrix/{id}` | Update a single permission entry |

---

## 3. Departments & Employees

| Method | Path | Purpose |
|---|---|---|
| GET | `/departments` | List departments |
| POST | `/departments` | Create department |
| PATCH | `/departments/{id}` | Update department |
| GET | `/employees` | List employees (filter by department, status) |
| POST | `/employees` | Create employee record |
| GET | `/employees/{id}` | Employee detail |
| PATCH | `/employees/{id}` | Update employee |
| DELETE | `/employees/{id}` | Mark employee as exited (soft delete) |

---

## 4. Job Descriptions

| Method | Path | Purpose |
|---|---|---|
| GET | `/job-descriptions` | List job descriptions (filter by department, status) |
| POST | `/job-descriptions` | Create job description |
| GET | `/job-descriptions/{id}` | Detail |
| PATCH | `/job-descriptions/{id}` | Update |
| DELETE | `/job-descriptions/{id}` | Close/archive |
| GET | `/job-descriptions/{id}/export` | Export as Word/PDF |
| GET | `/job-descriptions/{id}/scoring-criteria` | Get scoring rubric for this role |
| POST | `/job-descriptions/{id}/scoring-criteria` | Add/replace scoring criteria |
| PATCH | `/scoring-criteria/{id}` | Update one criterion |
| DELETE | `/scoring-criteria/{id}` | Remove one criterion |

---

## 5. CV Screening

| Method | Path | Purpose |
|---|---|---|
| POST | `/job-descriptions/{id}/candidates` | Upload CV(s) for this job description (multipart) |
| GET | `/job-descriptions/{id}/candidates` | List candidates for a job, with scores/rank if available |
| GET | `/candidates/{id}` | Candidate detail incl. parsed data |
| PATCH | `/candidates/{id}` | Manual field correction / status change |
| DELETE | `/candidates/{id}` | Remove candidate |
| POST | `/candidates/{id}/parse` | Trigger (re-)parsing of uploaded CV |
| POST | `/candidates/{id}/score` | Trigger (re-)scoring against job's criteria |
| POST | `/job-descriptions/{id}/rank` | Recompute ranking for all candidates on this job |
| GET | `/job-descriptions/{id}/ranking` | Get current ranked candidate list |
| POST | `/candidates/{id}/score-override` | Manual override of a candidate's score, with required reason (audit-logged) |
| GET | `/job-descriptions/{id}/report` | Export shortlist/ranking report (PDF/Excel) |

---

## 6. Attendance

| Method | Path | Purpose |
|---|---|---|
| GET | `/attendance-rules` | List attendance rule sets |
| POST | `/attendance-rules` | Create rule set |
| PATCH | `/attendance-rules/{id}` | Update rule set |
| GET | `/attendance` | List attendance records (filter by employee, department, date range) |
| POST | `/attendance` | Manually create/correct a record |
| PATCH | `/attendance/{id}` | Edit a record (requires reason, audit-logged) |
| POST | `/attendance/import` | Bulk import from biometric device export (Excel/CSV) |
| POST | `/attendance/sync-biometric` | Pull latest data from biometric device integration (stubbed until device access confirmed) |
| GET | `/attendance/summary` | Aggregated summary (present/absent/late days) per employee for a period — feeds payroll |
| GET | `/leave-requests` | List leave requests (filter by employee, status) |
| POST | `/leave-requests` | Submit leave request |
| PATCH | `/leave-requests/{id}` | Approve/reject leave request |

---

## 7. Payroll

| Method | Path | Purpose |
|---|---|---|
| GET | `/payroll-structures` | List pay structures (filter by employee) |
| POST | `/payroll-structures` | Create pay structure for an employee |
| PATCH | `/payroll-structures/{id}` | Update (e.g. salary revision, closes old with `effective_to`) |
| GET | `/payroll-runs` | List payroll runs (filter by month/year/status) |
| POST | `/payroll-runs` | Create new payroll run (draft) for a period |
| GET | `/payroll-runs/{id}` | Run detail incl. all payslips |
| POST | `/payroll-runs/{id}/generate` | Compute payslips for all employees using attendance + structure data |
| POST | `/payroll-runs/{id}/submit-for-approval` | Move to `pending_approval` |
| POST | `/payroll-runs/{id}/approve` | Approve run (requires payroll-approve permission) |
| POST | `/payroll-runs/{id}/mark-paid` | Mark run as paid |
| GET | `/payslips/{id}` | Single payslip detail |
| PATCH | `/payslips/{id}` | Manual adjustment before approval (audit-logged) |
| GET | `/payslips/{id}/pdf` | Download payslip PDF |
| GET | `/salary-advances` | List advances (filter by employee, status) |
| POST | `/salary-advances` | Request advance |
| PATCH | `/salary-advances/{id}` | Approve/reject/update recovery amount |

---

## 8. KPI

| Method | Path | Purpose |
|---|---|---|
| GET | `/kpi-definitions` | List KPI definitions (filter by department) |
| POST | `/kpi-definitions` | Create KPI definition |
| PATCH | `/kpi-definitions/{id}` | Update |
| DELETE | `/kpi-definitions/{id}` | Archive |
| GET | `/kpi-entries` | List KPI entries (filter by employee, department, period) |
| POST | `/kpi-entries` | Record actual value for an employee/period |
| PATCH | `/kpi-entries/{id}` | Correct an entry |
| GET | `/employees/{id}/kpi-summary` | Employee's KPI scores across a period |
| GET | `/departments/{id}/kpi-summary` | Department-level rollup |
| POST | `/departments/{id}/kpi-period-reviewed` | Mark period reviewed; emits `hr_admin.kpi.period_closed` |

---

## 9. Admin Control Panel

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/dashboard` | Aggregated stats across modules (headcount, open roles, pending approvals, attendance today, etc.) |
| GET | `/admin/audit-logs` | Paginated/filterable audit log (by user, action, entity, date range) |
| GET | `/admin/audit-logs/{id}` | Single log entry detail |
| GET | `/admin/system-config` | Get all runtime config key/values |
| PATCH | `/admin/system-config/{key}` | Update a config value |
| GET | `/admin/agent-status` | Health/status of this agent (and stub for sibling agents once registered) |

---

## 10. Integration (stub layer — expand only inside `interface.py`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/integration/health` | Liveness check for orchestrator |
| GET | `/integration/capabilities` | Machine-readable list of this agent's modules/events (mirrors `INTEGRATION_CONTRACT.md`) |
| POST | `/integration/events/subscribe` | Stub — future orchestrator event subscription |

These routes exist so the orchestrator has something to call, but internally they must only ever call through `app/integration/interface.py` — never directly into module internals.

---

## 11. Error Codes (shared vocabulary)

| Code | HTTP Status | Meaning |
|---|---|---|
| `unauthorized` | 401 | Missing/invalid token |
| `forbidden` | 403 | Valid token, insufficient permission |
| `not_found` | 404 | Entity doesn't exist |
| `validation_error` | 422 | Request body failed schema validation |
| `conflict` | 409 | e.g. duplicate attendance record for same day |
| `business_rule_violation` | 400 | e.g. approving an already-paid payroll run |
| `internal_error` | 500 | Unhandled server error |

All of these map to a consistent frontend error-handling pattern — see `FRONTEND_ARCHITECTURE.md`.
