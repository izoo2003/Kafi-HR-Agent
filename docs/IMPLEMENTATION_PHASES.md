# IMPLEMENTATION PHASES — HR & Admin Agent

> The build order. Read this at the start of every session to know what phase you're in, what's done, and what's next. Update the "Status" column as work progresses — this file is meant to be edited, not just read.

---

## How to Use This Doc

Each phase lists: what to build, which other docs govern it, and its exit criteria (what "done" means before moving to the next phase). Do not start a phase's frontend work before its backend is functional and tested — the split exists so each phase is independently verifiable. Do not jump ahead to a later phase's module because it seems easy — dependencies below are real, not arbitrary ordering.

---

## Phase 0 — Foundation Setup

**Backend:**
- Project scaffolding per `PROJECT_OVERVIEW.md` §3 folder structure
- `core/config.py`, `core/db.py`, `core/security.py`, `core/exceptions.py`
- Alembic setup, initial migration for `users`, `roles`, `user_roles`, `agent_access_matrix`, `permissions`, `role_permissions` (`DATABASE_SCHEMA.md` §1)
- Auth routes: `/auth/login`, `/auth/logout`, `/auth/refresh`, `/auth/me`
- `require_permission` dependency chain (`AUTH_AND_RBAC.md` §4)
- Seed migration: default roles (`AUTH_AND_RBAC.md` §1)

**Frontend:**
- Project scaffolding, routing shell, `AuthContext`, login page
- `components/ui/` primitives (Button, Table, Modal, Badge, Card, FormField, Pagination) per `UI_DESIGN_SYSTEM.md`
- Sidebar/top-bar layout shell

**Exit criteria:** can log in, see role-appropriate empty dashboard shell, no module pages yet. Auth + RBAC fully working end to end — this is the foundation every later phase depends on.

**Status:** ✅ Done (auth, RBAC, shell, tokens live)

---

## Phase 1 — Employees & Departments

**Backend:** `departments`, `employees` tables/models/schemas/routes/services (`DATABASE_SCHEMA.md` §2, `API_ENDPOINTS.md` §3).

**Frontend:** basic employee/department list + detail pages (not a full module of its own per the original scope, but every other module depends on employee data existing).

**Exit criteria:** can create departments and employees, link a `user` account to an `employee` record (needed for employee self-service row filtering later).

**Status:** ✅ Done (CRUD API + Employees UI)

**Depends on:** Phase 0

---

## Phase 2 — CV Screening

Full scope: `FEATURE_CV_SCREENING.md`.

**Backend build order:** job_descriptions → scoring_criteria → candidates (ingestion) → cv_parser → cv_scorer → candidate_ranker → pipeline.run_cv_pipeline → reporting exports.

**Frontend build order:** `JobDescriptionListPage`/`FormPage`/`DetailPage` → criteria builder → `CandidateListPage` (upload) → `RankingPage` → `CandidateDetailPage`.

**Exit criteria:** can create a job description, define scoring criteria, upload CVs, see them parsed/scored/ranked automatically, override a score, export a report.

**Status:** ✅ Core done (JD, criteria, upload/parse/score/rank + UI)

**Depends on:** Phase 1 (job descriptions link to departments; hiring converts a candidate to an employee)

---

## Phase 3 — Attendance

Full scope: `FEATURE_ATTENDANCE.md`.

**Backend build order:** attendance_rules → attendance_records (manual CRUD + status derivation service) → bulk import → leave_requests → attendance summary endpoint → biometric stub.

**Frontend build order:** `AttendanceOverviewPage` → `AttendanceRecordsPage` (manual + import) → `LeaveRequestsPage`.

**Exit criteria:** attendance rules configurable, manual attendance entry/edit working with correct status derivation, bulk import functional with row-level error feedback, leave requests submittable/approvable and correctly overriding attendance status, summary endpoint returns accurate aggregates.

**Status:** Done (rules, records, leave, import, summary, UI)

**Depends on:** Phase 1 (employees must exist to have attendance)

---

## Phase 4 — Payroll

Full scope: `FEATURE_PAYROLL.md`.

**Backend build order:** payroll_structures → deduction policy config seed → payroll_runs → pipeline.run_payroll_generation (consumes attendance summary from Phase 3) → salary_advances → payslip PDF export.

**Frontend build order:** `PayrollRunListPage` → `PayrollRunDetailPage` → `PayslipDetailPage` → `SalaryAdvancesPage`.

**Exit criteria:** can set up pay structures, generate a payroll run that correctly pulls attendance data and computes net pay including proration/overtime/deductions/advances, run goes through the full draft→approved→paid lifecycle with correct permission gating, payslip PDFs generate correctly.

**Status:** ⬜ Not started

**Depends on:** Phase 1, Phase 3 (payroll generation requires working attendance summaries — do not attempt this phase with attendance still incomplete/inaccurate, the payroll numbers will be wrong)

---

## Phase 5 — KPI

Full scope: `FEATURE_KPI.md`.

**Backend build order:** kpi_definitions (with weight validation, reuse pattern from scoring_criteria) → kpi_entries → rollup endpoints.

**Frontend build order:** `KpiDefinitionsPage` → `KpiDashboardPage`.

**Exit criteria:** can define department KPIs, record actuals, see accurate employee/department rollups with correct score-band coloring, mark a period reviewed.

**Status:** ✅ Done (definitions, entries, rollups, period close + UI)

**Depends on:** Phase 1 (departments/employees). Independent of Payroll/Attendance — can run in parallel with Phase 3/4 if working with multiple people, since it has no data dependency on them.

---

## Phase 6 — Admin Control Panel & Audit Log

Full scope: `FEATURE_ADMIN_PANEL.md`, `FEATURE_AUDIT_LOG.md`.

**Backend:** `audit_service.log_action` should actually already exist by this point (it's called by every prior phase's write operations per `FEATURE_AUDIT_LOG.md` §3 — if it wasn't built alongside Phase 1, retrofit it now and verify every prior phase's write actions are actually logging). Then: dashboard aggregation endpoint, user management routes, access matrix editor routes, system config routes, agent status endpoint.

**Frontend:** `DashboardPage`, `UserManagementPage` (incl. access matrix grid editor), `AuditLogPage`, `SystemConfigPage`.

**Exit criteria:** full admin panel functional; audit log shows accurate history from all prior phases (not just from this phase forward — verify retroactively that Phases 1–5 were logging correctly); access matrix editable and immediately affects permission checks; system config changes correctly affect payroll/KPI calculations.

**Status:** ⬜ Not started

**Depends on:** all prior phases (this is the control plane over everything built so far)

**Important:** audit logging should not actually be deferred to this phase — it's called out here because the *viewer UI* belongs here, but `audit_service.log_action` must be wired into every service function starting in Phase 1. Treat "does this action call `log_action`" as part of the exit criteria for every phase above, not just Phase 6.

---

## Phase 7 — Integration Hardening

Full scope: `INTEGRATION_CONTRACT.md`.

- Verify `integration/interface.py` implements every function in the contract doc, with real (not placeholder) logic for everything marked "today" behavior, and clean stub behavior for everything marked "later."
- Write the interface contract test suite (`BACKEND_ARCHITECTURE.md` §6) asserting signatures match the doc.
- Confirm no code outside `app/integration/` is what an external caller would need to import — a quick audit: could this whole agent be dropped into an orchestrator repo and only `interface.py` would need a wiring change?

**Exit criteria:** the "will this still work when this agent is one of many under one admin control plane?" test (`PROJECT_OVERVIEW.md` §4) can be answered yes for every module.

**Status:** ⬜ Not started

**Depends on:** all prior phases

---

## Cross-Phase Rules (apply throughout, not just at the end)

- Every phase's routes are added to `API_ENDPOINTS.md` if they weren't already fully specified there — that doc should stay in sync with reality, not drift.
- Every phase's tables are added to `DATABASE_SCHEMA.md` if a detail changes during implementation (e.g. a column added that wasn't foreseen) — update the doc in the same session.
- Never build an out-of-scope (kitchen/IT/generator/solar) feature "while you're in there" — even in Phase 6/7 when the admin panel might tempt adding utility-monitoring widgets. Route those to `NotOwnedByThisAgent` per `INTEGRATION_CONTRACT.md` §5.
