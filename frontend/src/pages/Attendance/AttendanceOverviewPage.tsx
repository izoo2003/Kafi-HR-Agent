import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { useAttendanceRecords, useAttendanceSummary } from "../../hooks/useAttendance";
import { useEmployees } from "../../hooks/useEmployees";
import { useAuth } from "../../hooks/useAuth";
import { isSelfService } from "../../lib/selfService";
import { ATTENDANCE_STATUS_LABELS } from "../../constants/statusLabels";

function monthRange(ym: string): { from: string; to: string } {
  const [y, m] = ym.split("-").map(Number);
  const from = `${y}-${String(m).padStart(2, "0")}-01`;
  const last = new Date(y, m, 0).getDate();
  const to = `${y}-${String(m).padStart(2, "0")}-${String(last).padStart(2, "0")}`;
  return { from, to };
}

export function AttendanceOverviewPage() {
  const { user, hasPermission } = useAuth();
  const selfService = isSelfService(user);
  const canWrite = hasPermission("attendance", "write");
  const now = new Date();
  const [month, setMonth] = useState(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`,
  );
  const [employeeId, setEmployeeId] = useState<number | "">(
    selfService && user?.linkedEmployeeId ? user.linkedEmployeeId : "",
  );
  const range = useMemo(() => monthRange(month), [month]);
  const employees = useEmployees({
    page: 1,
    pageSize: 100,
    status: "active",
    enabled: !selfService,
  });
  const scopedEmployeeId = selfService ? (user?.linkedEmployeeId ?? undefined) : employeeId === "" ? undefined : employeeId;
  const records = useAttendanceRecords({
    page: 1,
    pageSize: 200,
    dateFrom: range.from,
    dateTo: range.to,
    employeeId: scopedEmployeeId,
  });
  const summary = useAttendanceSummary(
    scopedEmployeeId
      ? { employeeId: scopedEmployeeId, periodStart: range.from, periodEnd: range.to }
      : null,
  );

  const byDate = useMemo(() => {
    const map = new Map<string, { status: string; count: number }>();
    for (const r of records.data?.items ?? []) {
      const cur = map.get(r.date) ?? { status: r.status, count: 0 };
      cur.count += 1;
      // prefer critical statuses when aggregating company view
      const rank: Record<string, number> = {
        absent: 5,
        late: 4,
        half_day: 3,
        on_leave: 2,
        present: 1,
        holiday: 0,
      };
      if ((rank[r.status] ?? 0) >= (rank[cur.status] ?? 0)) cur.status = r.status;
      map.set(r.date, cur);
    }
    return map;
  }, [records.data]);

  const daysInMonth = useMemo(() => {
    const [y, m] = month.split("-").map(Number);
    const last = new Date(y, m, 0).getDate();
    return Array.from({ length: last }, (_, i) => {
      const d = `${month}-${String(i + 1).padStart(2, "0")}`;
      return d;
    });
  }, [month]);

  return (
    <>
      <PageHeader
        title={selfService ? "My attendance" : "Attendance Overview"}
        breadcrumb="Attendance"
        actions={
          <>
            {canWrite ? (
              <Link to="/attendance/period-report">
                <Button variant="primary">Excel period report</Button>
              </Link>
            ) : null}
            <Link to="/attendance/records">
              <Button variant="secondary">{canWrite ? "Records & Import" : "Records"}</Button>
            </Link>
            <Link to="/attendance/leave-requests">
              <Button variant="primary">Leave Requests</Button>
            </Link>
          </>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
          <label className="form-field">
            <span className="form-field__label">Month</span>
            <input
              className="form-field__input"
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
            />
          </label>
          {selfService ? null : (
          <label className="form-field">
            <span className="form-field__label">Employee (for summary)</span>
            <select
              className="form-field__input"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">All (grid only)</option>
              {(employees.data?.items ?? []).map((e) => (
                <option key={e.id} value={e.id}>
                  {e.fullName} ({e.employeeCode})
                </option>
              ))}
            </select>
          </label>
          )}
        </div>

        {summary.data ? (
          <div
            style={{
              display: "grid",
              gap: "var(--space-3)",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            }}
          >
            {(
              [
                ["Present", summary.data.daysPresent, "present"],
                ["Late", summary.data.daysLate, "late"],
                ["Half day", summary.data.daysHalfDay, "half_day"],
                ["Absent", summary.data.daysAbsent, "absent"],
                ["On leave", summary.data.daysOnLeave, "on_leave"],
                ["OT hours", summary.data.overtimeHours, "info"],
              ] as const
            ).map(([label, value, status]) => (
              <Card key={label} status={status}>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)" }}>
                  {label}
                </div>
                <div className="font-data" style={{ fontSize: "var(--text-xl)" }}>
                  {value}
                </div>
              </Card>
            ))}
          </div>
        ) : null}

        {records.isLoading ? <Spinner label="Loading attendance" /> : null}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
            gap: "var(--space-2)",
          }}
        >
          {daysInMonth.map((d) => {
            const cell = byDate.get(d);
            const dayNum = d.slice(-2);
            const status = cell?.status ?? "neutral";
            return (
              <div
                key={d}
                data-status={status}
                className="card"
                style={{ padding: "var(--space-2)", minHeight: 64 }}
                title={d}
              >
                <div className="font-data" style={{ fontSize: "var(--text-xs)" }}>
                  {dayNum}
                </div>
                {cell ? (
                  <StatusBadge status={status}>
                    {ATTENDANCE_STATUS_LABELS[status as keyof typeof ATTENDANCE_STATUS_LABELS] ??
                      status}
                  </StatusBadge>
                ) : (
                  <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                    —
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
