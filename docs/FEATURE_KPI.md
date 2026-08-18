# FEATURE: KPI — HR & Admin Agent

> Covers in-scope item 5 (KPI definitions per department). Read alongside `DATABASE_SCHEMA.md` §6, `API_ENDPOINTS.md` §8.

---

## 1. End-to-End Flow

```
1. HR/Department Head defines KpiDefinitions for a department (name, target, weight, review period cadence)
2. During/after each review period, actuals are recorded per employee as KpiEntry rows
3. System computes a normalized score per entry, and rolls up per-employee and per-department summaries
4. At period close, KPI results feed into performance review conversations (and optionally KPI-linked bonus 
   logic in a later phase — not built now, don't half-implement it)
5. hr_admin.kpi.period_closed event emitted per department per period (INTEGRATION_CONTRACT.md §4)
```

---

## 2. KPI Definitions

- Scoped to a `department_id` — department KPIs are the HR-managed pack for a role. Self-service users may also create **personal** KPIs (`owner_employee_id` set to their employee id); those are excluded from department weight sums and rollups.
- Fields: `name`, `description`, `measurement_unit` (`%`, `count`, `score_1_5`, or others as needed — keep as a free-text unit label rather than a rigid enum, since departments will have varied metrics), `target_value`, `weight` (contribution to an overall department/employee score, same weighting principle as CV scoring criteria — weights across a department's active KPIs should sum to 1.0; create/update reject sums over 1.0 so KPIs can be added incrementally, and recording actuals requires an exact 1.0 sum), `review_period` (`monthly`/`quarterly`/`annual`). Personal KPI weights are validated separately (must not exceed 1.0).

### Default KPI packs (`POST /departments/{id}/kpi-definitions/seed-defaults`)

Idempotent, **department-specific** seed. Matched by department name (case-insensitive); unknown/custom departments get a generic pack. Each pack weights sum to 1.0 and includes **Other / ad-hoc work** (0.10). Names that already exist are skipped; remaining weight budget must fit new rows.

Examples:

| Department | Sample KPIs |
|---|---|
| IT | Ticket resolution, uptime, SLAs, security |
| Engineering | Feature delivery, code quality, sprint commitment |
| HR | Hiring, engagement, policy compliance, training |
| Sales | Quota attainment, new clients, pipeline, retention |
| Accounting | Month-end close, collections, audit readiness |
| Operations | On-time delivery, efficiency, quality, cost |
| Digital Marketing | Leads/campaigns, content cadence, engagement |
| Graphic Design | On-time delivery, quality, brand adherence |
| Customer Support | Resolution rate, first response, CSAT |
| General / other | Delivery, quality, SLAs, collaboration |

UI: **Add department default KPIs** on Dashboard + Definitions. HR can always add custom KPIs via the Definitions create form (archive a default if weight room is needed).

---

## 3. Recording Actuals (`KpiEntry`)

- One entry per `(kpi_definition_id, employee_id, period_start, period_end)` — recorded by a manager/HR (`recorded_by`), with an optional `notes` field for context (useful for review conversations later).
- Department overall rises only when actuals are saved through this path (weighted scores) — never via silent AI rewriting of scores.
- `score` is computed at entry time, not left for the frontend to derive:

```
normalized = actual_value / target_value   (capped at a configurable max, e.g. 1.5, so wildly 
             exceeding a target doesn't produce a distorted score — cap value stored in 
             system_config as "kpi.score_cap", default 1.5)
score = normalized * 100   (expressed as a percentage of target achievement)
```

- Score bands for the frontend status-color mapping (`UI_DESIGN_SYSTEM.md` §1 semantic tokens):
  - `score >= 90` → `--status-kpi-on-target`
  - `70 <= score < 90` → `--status-kpi-at-risk`
  - `score < 70` → `--status-kpi-below-target`
  These thresholds live in `system_config` (`kpi.score_bands`), not hardcoded in frontend or backend, so they're adjustable without a redeploy.

### Other / free-text + AI suggest (`POST /kpi/ai-suggest-entry`)

On Record actual, HR can describe work in a **Work done** textarea (especially when **Other / ad-hoc work** is selected). **Analyze with AI** calls Gemini (`GEMINI_API_KEY`) with `{ departmentId, employeeId, period, text }` and returns `{ kpiDefinitionId, actualValue, reasoning }` to prefill the form. The user must click **Save entry** — no auto-write. Without Gemini configured, a deterministic fallback maps to Other / ad-hoc with a rough count.

### Work submissions (`POST /kpi/work-submissions`)

Employees log work for **today only** (company timezone Asia/Karachi). Past and future dates are rejected. Sunday is not a workday (no logging; Sundays are omitted from daily score tables). Each workday is capped at 10 points. Multiple entries the same day append and add points until the cap. Employees who do not log on a workday count as **0**. Department score for a day is the average of all eligible employees (including zeros). Company score for a day is the average of departments that have eligible employees (including zeros). A month score averages workdays through today only — future days are not counted as 0 yet.

### Admin dashboard filters

| Scope | Grain | What admin sees |
|---|---|---|
| All departments | Month | Each workday’s company score (Mon–Sat; empty = 0; Sundays hidden) |
| One department | Month | Each workday’s department score + every employee log |
| All departments | Day | Each department’s score that day (missing employees = 0) + all logs |
| One department | Day | Every employee log in that department that day |

Default scope is **All departments** (no empty “select a department” gate). Click a day or a department row to drill in.

---

## 4. Rollups

### Employee-level (`GET /employees/{id}/kpi-summary`)
Contribution score = average of that employee’s daily scores (days they logged). Also returns department and company scores for the same period, plus the work items.

### Department-level (`GET /departments/{id}/kpi-summary`)
Average of employee contribution scores among those who logged work in the period, plus each employee's work items. Completeness is `employees_who_logged / eligible_employees`.

### Daily (`GET /kpi/daily-summary`)
One score per calendar day for the company (omit `department_id`) or one department.

### Work logs (`GET /kpi/work-logs`)
Individual dated entries for admin drill-down. Self-service callers only receive their own logs.

---

## 5. Period Close

- A period is "closed" conceptually once all active employees in a department have a `KpiEntry` for every active `KpiDefinition` for that `review_period` cycle — this isn't necessarily a hard status flag on a table (KPI doesn't need its own run/approval workflow like payroll), but the department-summary endpoint should clearly indicate completeness (`entries_recorded / entries_expected`) so HR knows when it's safe to consider the period final.
- `hr_admin.kpi.period_closed` event (per `INTEGRATION_CONTRACT.md` §4) is emitted when HR explicitly marks a period reviewed/closed via an action on the department summary page — not auto-inferred, since "is this period actually done" is a judgment call HR should make deliberately, not something the system silently decides.

---

## 6. Frontend Pages

- `KpiDefinitionsPage` — department KPI packs are seeded automatically; employees submit work from the dashboard rather than filling a criteria grid.
- `KpiDashboardPage` — defaults to all departments. Month view shows a score per day (company-wide or one department). Optional day filter drills into department scores or employee logs. Self-service users log work for a chosen date and see their month/department/company scores.
- App shell notification bell — polls unread in-app KPI reminders (~60s).

---

## 7. In-app KPI reminders (no email)

Scheduler (APScheduler, timezone **Asia/Karachi**) runs daily:

| Time | Kind | When |
|---|---|---|
| 18:00 | `kpi_incomplete` | Active KPI definitions exist and period completeness &lt; 100% |
| 18:20 | `kpi_at_risk` | Entries exist and department band is at-risk / below-target |

Notifications are written to `app_notifications` for users with `kpi` module permission ≥ `read`. API: `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/{id}/read`, `POST /notifications/read-all`. Email/WhatsApp KPI alerts are out of scope.

---

## 8. Edge Cases & Rules

- New employee mid-period: don't require a `KpiEntry` for a period they weren't present for the majority of — completeness calculation (§5) should account for `date_joined`/`date_exited` rather than expecting every active employee to have every period's entry regardless of tenure.
- Editing a `KpiDefinition`'s `target_value` or `weight` after entries already exist for the current period: existing `KpiEntry.score` values are **not** silently recomputed (unlike CV scoring's re-score-on-criteria-change behavior) — KPI actuals represent a point-in-time record against the target that was live *then*; changing the definition should apply going forward, prompting HR with a clear notice rather than retroactively rewriting historical scores.
- Record actual empty states: if the department has no active employees, instruct HR to assign Department on Employees; if no definitions, show **Add default KPIs**.
