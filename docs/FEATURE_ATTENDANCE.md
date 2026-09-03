# FEATURE: ATTENDANCE — HR & Admin Agent

> Covers in-scope item 3 (Attendance sheet format & rules) and the related system access item (biometric device — pull attendance data). Read alongside `DATABASE_SCHEMA.md` §4, `API_ENDPOINTS.md` §6, `BACKEND_ARCHITECTURE.md` (`ingestion/biometric_intake.py`).

---

## 1. End-to-End Flow

```
1. Admin configures AttendanceRules (shift times, grace period, half-day threshold) — company-wide or per-department
2. Attendance data enters the system via one of three sources:
   a. Biometric device sync (stub today — see §4)
   b. Bulk Excel/CSV import of device export
   c. Manual entry/correction by HR
3. Each check-in/check-out pair is evaluated against the applicable AttendanceRule to derive status (present/late/half_day/absent)
4. Leave requests are submitted, approved/rejected, and factored into attendance status (on_leave overrides absent)
5. Monthly attendance summary is computed per employee — this is what Payroll consumes (see FEATURE_PAYROLL.md)
```

---

## 2. Attendance Rules

- Multiple `AttendanceRule` rows can exist; a department-specific rule (`applies_to_department_id` set) takes precedence over the company-wide default (`applies_to_department_id = null`) for employees in that department.
- Fields: `shift_start`, `shift_end`, `grace_period_minutes` (minutes after `shift_start` before marked late), `half_day_threshold_minutes` (minimum minutes present to count as a half day rather than absent).
- Admin panel UI for managing rules lives under Attendance settings, not the general Admin Control Panel module — it's domain config, not system config.

**Status derivation logic** (`services/attendance_service.py`):
```
if no check_in and no check_out and not on approved leave and not a holiday:
    status = "absent"
elif on approved leave for this date:
    status = "on_leave"
elif marked as company holiday:
    status = "holiday"
else:
    minutes_late = check_in - shift_start (if positive)
    minutes_present = check_out - check_in
    if minutes_late > grace_period_minutes:
        status = "late"
    elif minutes_present < half_day_threshold_minutes:
        status = "half_day"
    else:
        status = "present"
```
This logic must live in one place (`attendance_service.py`), never duplicated in the import path vs manual-entry path vs biometric-sync path — all three converge on the same status-derivation function after writing raw check-in/check-out data.

---

## 3. Manual Corrections

- HR can create/edit any `AttendanceRecord` (`POST`/`PATCH /attendance`), always requires a `reason` in the request when editing an existing record (not required for creating a genuinely missing one), and is always audit-logged with before/after state — attendance edits directly affect payroll deductions, so this must be traceable.
- Unique constraint: one `AttendanceRecord` per `(employee_id, date)` — editing means updating that row, not creating a second one.

---

## 4. Biometric Device Integration (stub)

- `ingestion/biometric_client_stub.py` defines the expected interface now, even though no real device credentials exist yet:

```python
class BiometricDeviceClient(Protocol):
    def fetch_punches(self, since: datetime) -> list[RawPunchRecord]:
        """Returns raw check-in/check-out events since a given timestamp."""

class RawPunchRecord(BaseModel):
    device_employee_id: str    # device's own ID, mapped to Employee.employee_code
    timestamp: datetime
    punch_type: Literal["in", "out"]
```

- `POST /attendance/sync-biometric` calls this client; until real credentials exist (`backend/credentials/`), the stub returns an empty list and the endpoint responds with a clear message: "Biometric device not yet connected — use manual import." This keeps the endpoint and UI functional and testable now, real behavior swapped in later without changing the route or frontend.
- `device_employee_id` → `Employee` mapping: add an `external_device_id` column to `employees` when real device integration begins (flag this as a schema addition for that phase — not needed for the stub).

---

## 5. Bulk Import

- `POST /attendance/import` accepts an Excel/CSV file matching a defined template (columns: `employee_code, date, check_in, check_out`).
- Import is transactional per-row: valid rows are written (with `source = "import"`), invalid rows (unknown employee_code, malformed date, etc.) are collected and returned in the response as `{ imported: N, errors: [{ row: 3, message: "..." }] }` so HR can fix and re-upload just the failed rows rather than guessing.
- Import always runs the same status-derivation logic as §2 — imported rows are not stored as "present" by default.

---

## 6. Leave Requests

- Employee (or HR on their behalf) submits a `LeaveRequest` (`leave_type`, `start_date`, `end_date`, `reason`).
- Approval required from HR/department head (`PATCH /leave-requests/{id}`) before it affects attendance status — a `pending` leave request does not yet override attendance derivation; an `approved` one does, for every date in its range.
- Overlap validation: reject a new leave request if it overlaps an existing `approved` or `pending` request for the same employee (`business_rule_violation`).

---

## 7. Attendance Summary (feeds Payroll)

`GET /attendance/summary?employee_id=&period_start=&period_end=` returns, per employee:
```json
{
  "employee_id": 12,
  "period_start": "2026-07-01",
  "period_end": "2026-07-31",
  "days_present": 20,
  "days_late": 2,
  "days_half_day": 1,
  "days_absent": 1,
  "days_on_leave": 3,
  "total_working_days": 27,
  "overtime_hours": 0,
  "base_salary": 75000,
  "month_days": 30,
  "lates_per_off": 3,
  "late_absents": 0,
  "per_day_rate": 2500,
  "deduction_days": 1.5,
  "attendance_deduction": 3750,
  "estimated_net_salary": 71250
}
```
This exact shape is what `FEATURE_PAYROLL.md`'s payroll generation step consumes — any change to this response shape must be reflected in both docs in the same session.

---

## 8. Frontend Pages

- `AttendanceOverviewPage` — calendar/grid view, company or department-wide, day-by-day status color-coded via the status rail (`UI_DESIGN_SYSTEM.md` §4), quick filters.
- `AttendancePeriodReportPage` — WebHR Excel upload (one calendar month per file). After choosing a file, HR must pick **testing** (analyze only; nothing is written) or **professional** (overwrite attendance for that month, then overwrite the calculated salary sheet for the same month in Payroll). Names not yet in Employees are listed with a prompt to add them. Extra holiday dates are merged into `attendance.holidays` only in professional mode.
- `AttendanceRecordsPage` — tabular record list with manual add/edit, import button (with the error-row feedback from §5 surfaced inline), sync-biometric button (shows the "not yet connected" state honestly rather than pretending to sync). Monthly summary counts late/half-day as **present**; Absents are no-shows only; every 3 lates = 1 **late absent** (separate column).
- `LeaveRequestsPage` — list + approve/reject actions, filtered by department for department heads (row-level filtering per `AUTH_AND_RBAC.md` §6 for the `department_head` role). Admin list shows leave type **and** the employee's reason/notes (why they are taking leave), not type alone.

---

## 9. Edge Cases & Rules

- Public holidays: stored as `system_config` key `attendance.holidays` (JSON list of dates). HR can add more holiday dates when uploading the attendance Excel (`Add more holidays`); those dates are merged into this list **only on a professional upload** and are not counted as absent. A testing upload uses the extra dates for analysis only.
- Timezone: all `check_in`/`check_out` stored in UTC, converted to company-local time only at the presentation layer for shift-time comparisons — document the company's operating timezone in `system_config` so the comparison logic has a fixed reference rather than assuming server-local time.
- An employee with `status = "terminated"` should not appear in default attendance views/imports going forward, but historical records remain for payroll/reporting of their final pay period.
