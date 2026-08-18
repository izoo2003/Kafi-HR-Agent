# FEATURE: AUDIT LOG — HR & Admin Agent

> Covers in-scope item 7 (Audit log requirements for admin panel). Read alongside `DATABASE_SCHEMA.md` §7, `INTEGRATION_CONTRACT.md` §3.5 (`emit_audit_event`), and every other `FEATURE_*.md` doc's audit-logging callouts — this doc is the shared spec they all point back to.

---

## 1. Principle

Every write action that could matter later — for compliance, for dispute resolution ("why was my payslip this amount"), or for security review — is logged with enough detail to reconstruct what happened, who did it, and what changed. This is not a generic request log; it's a **business-action log**.

---

## 2. What Gets Logged

A non-exhaustive but representative list, drawn from every feature doc's callouts:

| Action | Entity Type | Notes |
|---|---|---|
| `auth.login_success` / `auth.login_failure` | — | includes IP address |
| `user.created` / `user.deactivated` | `user` | |
| `user.role_assigned` / `user.role_removed` | `user` | |
| `access_matrix.updated` | `agent_access_matrix` | before/after permission level |
| `system_config.updated` | `system_config` | before/after value |
| `job_description.created` / `.updated` / `.closed` | `job_description` | setting `open` also attempts LinkedIn feed posts |
| `scoring_criteria.updated` | `scoring_criteria` | |
| `candidate.score_override` | `candidate_score` | requires `reason`, before/after score |
| `candidate.status_changed` | `candidate` | shortlisted/rejected/hired |
| `attendance.manual_edit` | `attendance_record` | requires `reason`, before/after |
| `attendance.imported` | — | summary of import batch, not per-row |
| `leave_request.approved` / `.rejected` | `leave_request` | |
| `payroll_run.generated` | `payroll_run` | |
| `payroll_run.approved` / `.paid` | `payroll_run` | |
| `payslip.manual_adjustment` | `payslip` | requires reason, before/after |
| `salary_advance.approved` | `salary_advance` | |
| `payroll.salary_updated` | `employee` | base salary change |
| `payroll.sheet_adjusted` | `payroll_sheet_adjustment` | monthly salary-sheet extras |
| `kpi_definition.updated` | `kpi_definition` | |
| `kpi_entry.recorded` / `.corrected` | `kpi_entry` | |
| `kpi.period_marked_reviewed` | — | department + period |

**Rule of thumb for "should this be logged":** if reversing or explaining this action later would require asking "why did this change," it's logged. Simple reads are never logged (that would be a request log, not an audit log, and would bloat the table without adding value).

---

## 3. Logging Mechanism

- Every service function (`app/services/*.py`) that performs a qualifying write calls a shared helper at the end of its transaction:

```python
def log_action(db: Session, auth: AuthContext, action: str, entity_type: str, entity_id: int,
                before: dict | None = None, after: dict | None = None) -> None:
    """Writes an AuditLog row, then calls integration.interface.emit_audit_event 
    (per INTEGRATION_CONTRACT.md §3.5) so the same event is available to a future 
    orchestrator without a second logging call site."""
```

- This lives in `services/audit_service.py`, imported by every other service — not reimplemented per module. Consistency here is what makes the audit log actually trustworthy as a complete record rather than a patchwork of whichever developer remembered to log their feature.
- `before_state`/`after_state` are stored as JSON snapshots of just the changed fields (not the full row) where the entity is large, to keep log rows lean — but for small, high-stakes entities (scores, config values) storing the full before/after object is fine and clearer.

---

## 4. Retention

- No automatic deletion by default — audit logs are retained indefinitely unless a specific compliance requirement (not currently specified) dictates otherwise. If retention limits are needed later, this is a configuration addition (`system_config` key `audit_log.retention_days`) and an archival job, not a hard-coded cutoff — flag as a future need if raised, don't guess at a policy now.

---

## 5. Admin Panel Audit Log Viewer

`GET /admin/audit-logs` — paginated, filterable by:
- `user_id` (who did it)
- `action` (exact or prefix match, e.g. `payroll.*`)
- `entity_type` / `entity_id` (what was affected — supports "show me everything that happened to payslip #4021")
- `date_range`

`GET /admin/audit-logs/{id}` — full detail view including the before/after diff, rendered as a readable comparison (not raw JSON dump) in the frontend where the entity type has a known shape (payroll, attendance, candidate scores) — fall back to raw JSON display for less common entity types rather than building a custom diff view for every single one.

Frontend (`AuditLogPage`): table with columns Timestamp, User, Action, Entity, filter bar matching the query params above. Row click expands or navigates to the detail view. This page is read-only for everyone, including `super_admin` — audit logs are never editable or deletable through the application, by design (if a correction is ever needed, that's a database administration action outside the app, not a feature to build).

---

## 6. Access Control

- Only roles with `admin_panel` module `read` (or higher) access can view the audit log, per `AUTH_AND_RBAC.md`. The dedicated `readonly_auditor` role exists specifically for this — someone (e.g. a compliance reviewer) who should see everything but change nothing.
- The audit log itself is subject to the same row-level self-service restriction pattern used elsewhere: an `employee`-role user, if ever given any audit visibility at all (not default), would only see entries where `entity_type` relates to their own records — this isn't built by default since employees don't get audit access in the seed role set, but the row-filtering pattern from `AUTH_AND_RBAC.md` §6 is what to reach for if that need arises.

---

## 7. Relationship to `INTEGRATION_CONTRACT.md`

- `emit_audit_event` (§3.5 of that doc) is the single outbound seam — today it just triggers `audit_service.log_action`'s local DB write; later, the same call also publishes to a shared orchestrator event bus so sibling agents/orchestrator can build a unified cross-agent audit view without this agent needing to change anything about how it logs internally.
- Do not build a second, separate "event log" table for orchestrator purposes — `audit_logs` **is** the event log; the event bus (when it exists) is just another consumer of the same log_action call.
