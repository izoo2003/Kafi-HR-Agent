import { Fragment, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { useAttendancePeriodReport } from "../../hooks/useAttendance";
import { attendanceImportTemplateCsv } from "../../api/attendance";
import { ApiError } from "../../api/client";
import type { AttendancePeriodReport, PeriodEmployeeReport } from "../../types/attendance";

function dayTypeLabel(t: string): string {
  const map: Record<string, string> = {
    sunday_off: "Sunday off",
    saturday_off: "Saturday off (majority absent)",
    auto_holiday: "Auto holiday (≥80% absent)",
    configured_holiday: "Configured holiday",
  };
  return map[t] ?? t;
}

function EmployeeDetail({ emp }: { emp: PeriodEmployeeReport }) {
  return (
    <div
      style={{
        display: "grid",
        gap: "var(--space-3)",
        padding: "var(--space-3)",
        background: "var(--color-surface-alt)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div style={{ display: "grid", gap: 4, gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))" }}>
        <div>
          Leave allowance: <span className="num">{emp.leaveAllowance}</span> (used{" "}
          <span className="num">{emp.leaveUsed}</span>)
        </div>
        <div>
          Tenure: <span className="num">{emp.tenureMonths}</span> months
        </div>
        <div>
          Late → off days: <span className="num">{emp.lateOffDays}</span>
        </div>
        <div>
          Absents after leave: <span className="num">{emp.absentsAfterLeave}</span>
        </div>
        <div>
          OT bonus days: <span className="num">{emp.overtimeBonusDays}</span>
        </div>
        <div>
          Deduction days: <span className="num">{emp.deductionDays}</span>
        </div>
        <div>
          Per day (salary/30): <span className="num">{emp.perDayRate.toFixed(2)}</span>
        </div>
        <div>
          Est. deduction: <span className="num">{emp.estimatedDeductionAmount.toFixed(2)}</span>
        </div>
        <div>
          Est. OT pay: <span className="num">{emp.estimatedOvertimeAmount.toFixed(2)}</span>
        </div>
        <div>
          Est. net: <span className="num">{emp.estimatedNetSalary.toFixed(2)}</span>
        </div>
      </div>

      {emp.lateEvents.length > 0 ? (
        <div>
          <strong>Late days &amp; times</strong>
          <ul style={{ margin: "8px 0 0", paddingLeft: "1.2rem" }}>
            {emp.lateEvents.map((e) => (
              <li key={`${e.date}-${e.checkInTime}`}>
                <span className="num">{e.date}</span> at{" "}
                <span className="num">{e.checkInTime}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
          No late check-ins.
        </p>
      )}

      {emp.halfDayDates.length > 0 ? (
        <div>
          <strong>Half days (after 11:30)</strong>
          <p style={{ margin: "4px 0 0" }} className="num">
            {emp.halfDayDates.join(", ")}
          </p>
        </div>
      ) : null}

      {emp.absentDates.length > 0 ? (
        <div>
          <strong>Absent dates</strong>
          <p style={{ margin: "4px 0 0" }} className="num">
            {emp.absentDates.join(", ")}
          </p>
        </div>
      ) : null}

      {emp.overtimeDates.length > 0 ? (
        <div>
          <strong>OT days (present on holiday / Saturday off)</strong>
          <p style={{ margin: "4px 0 0" }} className="num">
            {emp.overtimeDates.join(", ")}
          </p>
        </div>
      ) : null}
    </div>
  );
}

export function AttendancePeriodReportPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const analyze = useAttendancePeriodReport();
  const [report, setReport] = useState<AttendancePeriodReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function onUpload(files: FileList | null) {
    if (!files?.[0]) return;
    setError(null);
    setReport(null);
    setExpanded(null);
    try {
      const res = await analyze.mutateAsync(files[0]);
      setReport(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Period report failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Attendance period report"
        breadcrumb="Attendance / Period report"
        actions={
          <Link to="/attendance/records">
            <Button variant="secondary">Records</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <Card>
          <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Upload Excel / CSV</h2>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Upload the WebHR attendance export as-is (
            <strong>Employee ID</strong>, <strong>First Name</strong>, <strong>Date</strong>,{" "}
            <strong>First Punch</strong>). Period comes from dates in the file. Keep Employee ID =
            this app&apos;s employee code and First Name = full name so we can pull{" "}
            <strong>base salary</strong> and save attendance. First Punch only drives late /
            half-day / presence. Rules: on time until 09:40, late from 09:41, after 11:30 = late +
            half day, Sunday off, Saturday/auto holiday when ≥80% absent, 3 lates = 1 off.
          </p>
          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              style={{ display: "none" }}
              onChange={(e) => {
                void onUpload(e.target.files);
                e.target.value = "";
              }}
            />
            <Button
              type="button"
              variant="primary"
              disabled={analyze.isPending}
              onClick={() => fileRef.current?.click()}
            >
              {analyze.isPending ? "Analyzing…" : "Upload & analyze"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const blob = new Blob([attendanceImportTemplateCsv()], { type: "text/csv" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "attendance_period_template.csv";
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              Download template
            </Button>
          </div>
        </Card>

        {error ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{error}</p> : null}
        {analyze.isPending ? <Spinner label="Processing attendance file" /> : null}

        {report ? (
          <>
            <Card>
              <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Period summary</h2>
              <p style={{ margin: 0 }}>
                <span className="num">{report.periodStart}</span> →{" "}
                <span className="num">{report.periodEnd}</span>
                {" · "}late after <span className="num">{report.lateAfter}</span>
                {" · "}half day after <span className="num">{report.halfDayAfter}</span>
                {" · "}
                <span className="num">{report.latesPerOff}</span> lates = 1 off
                {" · "}month days <span className="num">{report.monthDays}</span>
                {" · "}imported <span className="num">{report.importedRows}</span> rows
              </p>
              {report.nonWorkingDays.length > 0 ? (
                <ul style={{ marginTop: "var(--space-3)", paddingLeft: "1.2rem" }}>
                  {report.nonWorkingDays.map((d) => (
                    <li key={d.date}>
                      <span className="num">{d.date}</span> ({d.weekday}) — {dayTypeLabel(d.dayType)}
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                  No auto Saturday-off / holiday days detected in this file.
                </p>
              )}
              {report.errors.length > 0 ? (
                <p style={{ color: "var(--color-status-warning)", fontSize: "var(--text-sm)" }}>
                  Row errors: {report.errors.map((e) => `R${e.row}: ${e.message}`).join("; ")}
                </p>
              ) : null}
            </Card>

            <Table
              headers={[
                "Employee",
                "Present",
                "Late",
                "Half day",
                "Absent",
                "OT days",
                "Est. net",
                "Details",
              ]}
            >
              {report.employees.map((emp) => (
                <Fragment key={emp.fullName}>
                  <tr data-status={emp.daysAbsent > 0 ? "warning" : "positive"}>
                    <td>
                      <div>{emp.fullName}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                        {emp.matchedEmployee
                          ? emp.employeeCode || "Linked employee"
                          : "Excel name only (no employee link)"}
                      </div>
                    </td>
                    <td className="num">{emp.daysPresent}</td>
                    <td className="num">{emp.daysLate}</td>
                    <td className="num">{emp.daysHalfDay}</td>
                    <td className="num">{emp.daysAbsent}</td>
                    <td className="num">{emp.overtimeBonusDays}</td>
                    <td className="num">{emp.estimatedNetSalary.toFixed(2)}</td>
                    <td>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          setExpanded(expanded === emp.fullName ? null : emp.fullName)
                        }
                      >
                        {expanded === emp.fullName ? "Hide" : "Show"}
                      </Button>
                    </td>
                  </tr>
                  {expanded === emp.fullName ? (
                    <tr>
                      <td colSpan={8}>
                        <EmployeeDetail emp={emp} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </Table>
          </>
        ) : null}
      </div>
    </>
  );
}
