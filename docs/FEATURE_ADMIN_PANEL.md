# FEATURE: ADMIN CONTROL PANEL — HR & Admin Agent

> Covers in-scope items 6 & 7 (User Role Matrix, Admin Panel/Audit Log requirements) as they surface in the UI. Read alongside `AUTH_AND_RBAC.md` (the matrix this panel manages), `FEATURE_AUDIT_LOG.md` (the log this panel surfaces), `API_ENDPOINTS.md` §9.

---

## 1. Purpose

The Admin Control Panel is where a `super_admin` (or scoped roles like `hr_manager` for user management within HR) manages the system itself: who has access to what, what's happened, and how the system is configured. It is **not** where day-to-day HR work happens (that's the module-specific pages) — it's the control plane sitting above them, and it's the part of this agent most directly designed to generalize into a shared multi-agent admin panel later (per `PROJECT_OVERVIEW.md` §4).

---

## 2. Sub-Pages

### 2.1 Dashboard (`GET /admin/dashboard`)
High-level operational snapshot, not a KPI/payroll deep-dive (those live in their own modules):
```json
{
  "headcount_active": 142,
  "open_job_descriptions": 5,
  "candidates_pending_review": 12,
  "attendance_today": { "present": 130, "absent": 4, "on_leave": 8 },
  "payroll_runs_pending_approval": 1,
  "leave_requests_pending": 6
}
```
Each figure links through to the relevant module page (dashboard is a jump-off point, not a dead end) — e.g. clicking "1 payroll run pending approval" goes straight to that run.

### 2.2 User Management (`UserManagementPage`)
- List all `users`, their assigned `roles`, `is_active` status, `last_login_at`.
- Create user, assign/remove roles, deactivate (never hard-delete a user — soft-delete via `is_active`, preserves audit trail integrity since `audit_logs.user_id` references must remain valid).
- **Access Matrix editor:** a dedicated view of `agent_access_matrix` — rows = roles, columns = modules (job_descriptions, cv_screening, attendance, payroll, kpi, admin_panel), cells = permission level dropdown (`none/read/write/approve/admin`). This is the literal UI for in-scope item 6 (complete user role matrix). Since `agent_key` is already a column in the matrix (per `DATABASE_SCHEMA.md` §1), this same UI is designed to grow an "agent" dimension when sibling agents join — build the table/grid component generically (rows/cols/cells from data, not hardcoded module list) so that's a data change, not a UI rewrite.

### 2.3 Audit Log Viewer (`AuditLogPage`)
Full spec in `FEATURE_AUDIT_LOG.md` — this page is the log's primary consumer.

### 2.4 System Config (`SystemConfigPage`)
- Editable view of `system_config` key/values referenced throughout the other feature docs: `payroll.deduction_policy`, `kpi.score_cap`, `kpi.score_bands`, attendance holiday list, etc.
- Rendered as a grouped form (grouped by the config key's module prefix — `payroll.*`, `kpi.*`, `attendance.*`) rather than a raw JSON editor, so non-technical admins can safely adjust values; raw JSON edit available as an "advanced" toggle for configs too structurally complex for a simple form (e.g. `kpi.score_bands`' array of threshold objects).
- Every change here is audit-logged (`system_config.updated`) with before/after value — config changes materially affect payroll/KPI calculations, so this is high-stakes and must be traceable.

### 2.5 Agent Status (`GET /admin/agent-status`)
- Shows this agent's own health (`integration.interface.health_check()` result) and, once an orchestrator exists, sibling agents' status too (today: shows this agent only, with a clear "standalone mode" indicator rather than pretending other agents are integrated).

---

## 3. Permissions for This Module

Per `AUTH_AND_RBAC.md`: `admin_panel` module access is intentionally the most restricted — default seed gives only `super_admin` full (`admin`) access. `hr_manager` might get `write` on User Management specifically but not System Config, if finer-grained control is needed — use the fine-grained `permissions` table (`AUTH_AND_RBAC.md` §2) for this split rather than trying to force it into the coarser module-level matrix (e.g. `admin_panel.users.write` vs `admin_panel.config.write` as distinct permission codes).

---

## 4. Frontend Layout Notes

- Admin Panel gets its own top-level nav section (separate from the HR-function modules), visually distinguished as "system" territory — per `UI_DESIGN_SYSTEM.md`, still uses the same tokens/components, just grouped separately in the sidebar so it doesn't get mistaken for a day-to-day HR page.
- The Access Matrix editor and System Config pages should have an explicit "unsaved changes" guard (confirm before navigating away) given how consequential a mis-click here could be.

---

## 5. Multi-Agent Forward-Compatibility

This is the module most likely to be directly replaced or absorbed by a real orchestrator's admin UI later. Keep it decoupled:
- Dashboard stats are fetched from this agent's own `/admin/dashboard` — don't hardcode cross-agent stats here; if a future orchestrator wants a unified dashboard across agents, that's the orchestrator's own aggregation layer calling each agent's `/integration/capabilities` and `/admin/dashboard`-equivalent, not this agent reaching into siblings' data.
- The Access Matrix UI's generic rows/cols/cells design (§2.2) is the main piece of forward-compatibility work in this module — get that right now rather than hardcoding a 6-column table for just this agent's modules.
