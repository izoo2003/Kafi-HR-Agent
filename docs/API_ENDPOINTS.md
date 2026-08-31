# API ENDPOINTS — HR & Admin Agent

> All routes prefixed with `/api/v1`. All routes (except `/auth/login`, `/auth/register`, and `/auth/register-options`) require a valid JWT bearer token. All routes are additionally gated by the RBAC permission matrix — see `AUTH_AND_RBAC.md`. Request/response bodies are Pydantic models defined under `backend/app/schemas/`; frontend TS types under `frontend/src/types/` must mirror them exactly.

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
| POST | `/auth/login` | Username or email + PIN/password, returns JWT | none |
| POST | `/auth/register` | Self-service signup (username + PIN + department); creates `employee` user + linked employee | none |
| GET | `/auth/register-options` | Public department list for the signup form | none |
| POST | `/auth/logout` | Invalidate session/token | required |
| POST | `/auth/refresh` | Refresh access token | required (refresh token) |
| GET | `/auth/me` | Current user profile + roles + permissions + linked employee | required |

---

## 2. Users & Roles (Admin Panel)

| Method | Path | Purpose |
|---|---|---|
| GET | `/users` | List users (paginated). Includes `username`, `login_identifier`, and `login_pin` so an admin can view stored PINs. |
| POST | `/users/{id}/set-password` | Admin sets a new password/PIN; response includes the new password once so it can be shared |
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
| GET | `/departments` | List departments (any signed-in user; needed for self-service KPI/attendance). JD/SOP text and attachments are included for HR (`employees` read) or for the caller's own department only |
| GET | `/departments/me` | Signed-in user's assigned department with job description, SOPs, and attachments |
| POST | `/departments` | Create department |
| POST | `/departments/ai-draft` | Generate Job Description or SOP text from the department name (`kind`: `job_description` \| `sop`) |
| PATCH | `/departments/{id}` | Update department |
| DELETE | `/departments/{id}` | Remove department (blocked if employees or other records still use it) |
| POST | `/departments/{id}/documents` | Upload JD/SOP attachments (multipart: `kind`, `files[]`) — PDF or image |
| GET | `/departments/{id}/documents/{document_id}/file` | Download/preview a department attachment (HR, or the employee whose department it is) |
| DELETE | `/departments/{id}/documents/{document_id}` | Remove a department attachment |
| GET | `/employees` | List employees (filter by department, status) |
| POST | `/employees` | Create employee record (personal, role/department, bank, salary fields) |
| POST | `/cnic/verify` | Verify typed CNIC + front/back card images (format + OCR match; images only, not NADRA). Prefer this path. |
| POST | `/education-documents/verify` | Upload one or more education documents (multipart `documents[]`, PDF or image); AI reads them and checks whether named schools/colleges/universities appear to be real institutions (not an official registry lookup). |
| POST | `/employees/cnic/verify` | Deprecated alias of `/cnic/verify` |
| GET | `/employees/{id}` | Employee detail incl. documents + references |
| GET | `/employees/{id}/letters/appointment` | Download stored appointment letter (404 if not created yet) |
| GET | `/employees/{id}/letters/contract` | Download stored employment contract (404 if not created yet) |
| POST | `/employees/{id}/letters/appointment` | Generate, store, and download appointment letter Word file |
| POST | `/employees/{id}/letters/contract` | Generate, store, and download employment contract Word file |
| POST | `/employees/{id}/letters/appointment/verify` | Upload signed letter image; AI confirms it is an appointment letter **and** a handwritten signature is present → Verified, otherwise rejected |
| POST | `/employees/{id}/letters/contract/verify` | Upload signed contract image; AI confirms it is an employment contract **and** a handwritten signature is present → Verified, otherwise rejected |
| PATCH | `/employees/{id}` | Update employee profile fields |
| DELETE | `/employees/{id}` | Mark employee as exited (soft delete) |
| POST | `/employees/{id}/documents` | Upload document(s) (multipart: `category`, optional `title`, `files[]`) — PDF/images; binaries go to Supabase Storage when configured |
| GET | `/employees/{id}/documents/{document_id}/file` | Download an employee document (from Supabase Storage or legacy local path) |
| DELETE | `/employees/{id}/documents/{document_id}` | Remove an employee document |
| POST | `/employees/{id}/references` | Add a client referral (name, CNIC, relation, phone) |
| PATCH | `/employees/{id}/references/{reference_id}` | Update a client referral |
| DELETE | `/employees/{id}/references/{reference_id}` | Remove a client referral (and its files) |
| POST | `/employees/{id}/references/{reference_id}/documents` | Upload referral CNIC/related files (multipart `files[]`) |
| GET | `/employees/{id}/references/{reference_id}/documents/{document_id}/file` | Download a reference document |
| DELETE | `/employees/{id}/references/{reference_id}/documents/{document_id}` | Remove a reference document |
| GET | `/hr-policies` | HR policies document (any signed-in user) |
| PUT | `/hr-policies` | Replace the HR policies document (`employees` write); stored in `system_config` key `hr.policies` |

---

## 4. Job Descriptions

| Method | Path | Purpose |
|---|---|---|
| GET | `/job-descriptions` | List job descriptions (filter by department, status); includes `applicants_count` |
| POST | `/job-descriptions` | Create job description (auto-appends Google Form apply link if missing) |
| GET | `/job-descriptions/application-form` | Configured public Google Form URL for CV/details submission |
| GET | `/job-descriptions/linkedin-accounts` | Configured LinkedIn profile names/labels for the Open-job picker (no tokens) |
| POST | `/job-descriptions/ai-draft` | AI Analyzer: generate description (with hashtags) + requirements + skills; appends Google Form link |
| POST | `/job-descriptions/ai-image` | Generate hiring poster image (Cloudflare Workers AI + layout); returns PNG base64; sets description `Apply Here -> {Google Form URL}` |
| GET | `/job-descriptions/{id}` | Detail (includes `applicants_count`, `application_form_url`, `image_paths`, `linkedin_posts`) |
| PATCH | `/job-descriptions/{id}` | Update; setting status to `open` with `linkedin_account_names` posts to those LinkedIn accounts |
| DELETE | `/job-descriptions/{id}` | Close/archive |
| POST | `/job-descriptions/{id}/images` | Upload posting image(s) (multipart, PNG/JPG/WEBP/GIF, max 8) |
| GET | `/job-descriptions/{id}/images/{index}/file` | Download posting image by index |
| DELETE | `/job-descriptions/{id}/images/{index}` | Remove posting image |
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
| GET | `/candidates/{id}/cv` | Original CV/resume file (PDF, DOCX, TXT, or image) — inline for preview |
| PATCH | `/candidates/{id}` | Manual field correction / status change |
| DELETE | `/candidates/{id}` | Remove candidate |
| POST | `/candidates/{id}/parse` | Trigger (re-)parsing of uploaded CV |
| POST | `/candidates/{id}/score` | Trigger (re-)scoring against job's criteria |
| POST | `/job-descriptions/{id}/rank` | Recompute ranking for all candidates on this job |
| GET | `/job-descriptions/{id}/ranking` | Get current ranked candidate list |
| POST | `/candidates/{id}/score-override` | Manual override of a candidate's score, with required reason (audit-logged) |
| GET | `/job-descriptions/{id}/report` | Export shortlist/ranking report (PDF/Excel) |
| POST | `/cv-screening/sync` | Fetch new CVs from enabled sources (default: HR webmail `hr@kafi-group.com` + Google Form), AI-match / unassigned pool (see `FEATURE_CV_SCREENING.md` §11) |
| GET | `/candidates/unassigned` | List candidates fetched automatically that aren't yet matched/assigned to a job |
| POST | `/candidates/{id}/assign` | Manually assign an unassigned (or misassigned) candidate to a job description, then re-runs the scoring pipeline |
| GET | `/candidates/{id}/scores` | Per-criterion scores for a candidate |
| GET | `/candidates/{id}/evaluation` | AI-style hire recommendation summary; returns `business_rule_violation` if the candidate has no `job_description_id` yet — assign it first |
| POST | `/candidates/{id}/hire` | Convert a candidate to an `Employee` record, emits `hr_admin.candidate.hired` |

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
| POST | `/attendance/import` | Bulk import from biometric device export (Excel/CSV; `name` or `employee_code` + date + check_in) |
| POST | `/attendance/period-report` | Upload Excel/CSV → office policy report. Form: `saturday_off_mode` (`second_saturday` Recommended / `date`) + optional `saturday_off_date`; optional `extra_holiday_dates` (comma-separated YYYY-MM-DD extra holidays, not counted as absent). |
| POST | `/attendance/sync-biometric` | Pull latest data from biometric device integration (stubbed until device access confirmed) |
| GET | `/attendance/summary` | Aggregated summary (present/absent/late days) per employee for a period, plus attendance-based net salary (`late_absents` = lates ÷ 3, deduction from absents + late-offs + half days) |
| GET | `/leave-requests` | List leave requests (filter by employee, status); includes `reason` and employee name; self-service sees own only |
| POST | `/leave-requests` | Submit leave (self-service: own employee only with attendance read; HR needs write for others) |
| PATCH | `/leave-requests/{id}` | Approve/reject leave request (attendance approve) |

---

## 7. Payroll

| Method | Path | Purpose |
|---|---|---|
| GET | `/payroll/salaries` | List active employees with current `base_salary` (paginated) |
| PATCH | `/payroll/salaries/{employee_id}` | Update an active employee's `base_salary` (audit-logged; requires payroll write) |
| GET | `/payroll/compute` | Net salary for month/year using attendance + selected tax year (`tax_year_id`); includes salary-sheet columns and any saved AI summary for that month |
| GET | `/payroll/compute/export` | Download the month's salary sheet as Excel (Kafi salary-sheet layout + Payment Summary; includes AI summary on the sheet and an AI Summary tab when one has been generated) |
| POST | `/payroll/compute/ai-summary` | Generate AI narrative, persist it on the month's salary sheet (`system_config` `payroll.ai_summary.{YYYY-MM}`), and return it so the sheet + Excel download include it |
| PUT | `/payroll/sheet-adjustments` | Save monthly salary-sheet extras (allowance, loan, advance, payment mode, remarks) and optional base salary |
| GET | `/payroll/tax-years` | List tax years with progressive slabs |
| POST | `/payroll/tax-years` | Create a tax year (optional initial slabs) |
| GET | `/payroll/tax-years/{id}` | Tax year detail |
| PATCH | `/payroll/tax-years/{id}` | Update tax year metadata |
| PUT | `/payroll/tax-years/{id}/slabs` | Replace all slabs for a tax year (editable for future FY changes) |
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
| GET | `/employees/{id}/kpi-summary` | Employee's contribution + department/global scores for a period |
| GET | `/departments/{id}/kpi-summary` | Department rollup with each employee's logs |
| GET | `/kpi/global-summary` | Company rollup: score per department for a period |
| GET | `/kpi/daily-summary` | Score per calendar day (`department_id` optional; omit = company-wide) |
| GET | `/kpi/work-logs` | Individual work logs (`department_id`, `employee_id`, date range) |
| POST | `/kpi/work-submissions` | Employee self-service: log work for today (max 10 pts/day); `effort_level` + `points_to_add` clamped by effort tier |
| POST | `/departments/{id}/kpi-period-reviewed` | Mark period reviewed; emits `hr_admin.kpi.period_closed` |
| POST | `/departments/{id}/kpi-definitions/seed-defaults` | Idempotent default KPI pack (incl. Other / ad-hoc; weights sum to 1.0) |
| POST | `/kpi/ai-suggest-entry` | Gemini formats work + `effort_level` / `effort_score` / `points_to_add` by workload (no write; user confirms Save) |
| GET | `/employee-performance` | Employee Development: month KPI entries + live/finalized score out of 10 + history (`employee_id`, `period_year`, `period_month`) |
| POST | `/employee-performance/ai-summary` | Generate/refresh Gemini performance summary for employee+month (requires kpi write) |
| POST | `/employee-training/recommend` | AI intermediate/advanced course recommendations for employee + topic (kpi write) |
| POST | `/employee-training/assign` | Persist selected recommended courses to employee (Things To Learn) |
| GET | `/employee-training` | List training assignments (`employee_id` optional; self-service = own only) |
| PATCH | `/employee-training/{id}` | Update assignment status (`assigned` / `in_progress` / `completed`) |
| POST | `/employee-resignations/generate` | Generate letter text (self-service = own first-person letter; HR = confirmation letter) |
| GET | `/employee-resignations` | List notices (`employee_id` optional; self-service = own only) |
| POST | `/employee-resignations` | HR: send letter to employee (`direction=hr`, `pending`). Self-service: save draft or `submit=true` to send to HR (`direction=employee`) |
| GET | `/employee-resignations/{id}` | Notice detail |
| PATCH | `/employee-resignations/{id}` | Employee: edit `draft`/`rejected` own letter. HR: edit pending HR-issued letter or set `status=cancelled` |
| DELETE | `/employee-resignations/{id}` | Employee: delete own `draft`/`rejected`. HR: delete non-accepted HR-issued notice |
| POST | `/employee-resignations/{id}/submit` | Employee sends `draft`/`rejected` letter to HR (`pending`) |
| POST | `/employee-resignations/{id}/withdraw` | Employee pulls pending letter back to `draft` |
| POST | `/employee-resignations/{id}/accept` | HR-issued: employee accepts. Employee-authored: HR accepts. Then terminate employee + deactivate login |
| POST | `/employee-resignations/{id}/reject` | HR rejects employee-submitted letter (optional reason); employee can edit and resend |

### Notifications (in-app)

| Method | Path | Purpose |
|---|---|---|
| GET | `/notifications` | List current user's notifications (paginated; `unread_only` filter) |
| GET | `/notifications/unread-count` | Unread badge count |
| POST | `/notifications/{id}/read` | Mark one notification read |
| POST | `/notifications/read-all` | Mark all unread notifications read |

KPI reminder jobs (Asia/Karachi 18:00 incomplete / 18:20 at-risk) insert rows; no email.

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
| GET | `/integrations/whatsapp/webhook` | Meta WhatsApp Cloud API verify challenge (`hub.verify_token`) — no JWT |
| POST | `/integrations/whatsapp/webhook` | Meta WhatsApp webhook: queue inbound PDF/DOCX for Sync CVs (HMAC signature) |

Orchestrator-facing routes call through `app/integration/interface.py`. The WhatsApp webhook is Meta-facing: it only writes the inbound queue, then Sync CVs drains it.

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
