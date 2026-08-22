import { Fragment, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import {
  MonthlyAttendanceGrid,
  aggregateAttendanceTotals,
} from "../../components/domain/MonthlyAttendanceGrid";
import {
  useAttendancePeriodReport,
  useCreateEmployeesFromAttendanceExcel,
} from "../../hooks/useAttendance";
import { attendanceImportTemplateCsv } from "../../api/attendance";
import { ApiError } from "../../api/client";
import type {
  AttendancePeriodReport,
  PeriodEmployeeReport,
  SaturdayOffMode,
} from "../../types/attendance";

function dayTypeLabel(t: string): string {
  const map: Record<string, string> = {
    sunday_off: "Sunday off",
    saturday_off: "Saturday off",
    auto_holiday: "Company off (≥90% absent)",
    configured_holiday: "Configured holiday",
  };
  return map[t] ?? t;
}

function isSaturdayIso(iso: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return false;
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).getDay() === 6;
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
          Excel ID: <span className="num">{emp.excelEmployeeId ?? "—"}</span>
        </div>
        <div>
          Leave allowance: <span className="num">{emp.leaveAllowance}</span> (used{" "}
          <span className="num">{emp.leaveUsed}</span>)
        </div>
        <div>
          Tenure: <span className="num">{emp.tenureMonths}</span> months
        </div>
        <div>
          Late → absent days: <span className="num">{emp.lateOffDays}</span>
        </div>
        <div>
          Absents after leave: <span className="num">{emp.absentsAfterLeave}</span>
        </div>
        <div>
          Sundays present: <span className="num">{emp.daysSundayPresent}</span>
        </div>
        <div>
          OT days: <span className="num">{emp.overtimeBonusDays}</span>
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
          <strong>Half days (after 11:30) — still counted as present</strong>
          <p style={{ margin: "4px 0 0" }} className="num">
            {emp.halfDayDates.join(", ")}
          </p>
        </div>
      ) : null}

      {(emp.sundayDates ?? []).length > 0 ? (
        <div>
          <strong>Sundays present (OT, not present)</strong>
          <p style={{ margin: "4px 0 0" }} className="num">
            {emp.sundayDates.join(", ")}
          </p>
        </div>
      ) : null}

      {emp.absentDates.length > 0 ? (
        <div>
          <strong>Absent dates (working days only)</strong>
          <p style={{ margin: "4px 0 0" }} className="num">
            {emp.absentDates.join(", ")}
          </p>
        </div>
      ) : null}

      {emp.overtimeDates.length > 0 ? (
        <div>
          <strong>OT days (present on Sunday / Saturday off / company off)</strong>
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
  const lastFileRef = useRef<File | null>(null);
  const analyze = useAttendancePeriodReport();
  const addEmployees = useCreateEmployeesFromAttendanceExcel();
  const [report, setReport] = useState<AttendancePeriodReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [reportView, setReportView] = useState<"summary" | "monthly">("summary");
  const [saturdayOffMode, setSaturdayOffMode] = useState<SaturdayOffMode>("second_saturday");
  const [saturdayOffDate, setSaturdayOffDate] = useState("");
  const unmatched = report?.unmatchedPeople ?? [];
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const selectedPeople = useMemo(
    () => unmatched.filter((p) => selected[`${p.fullName}|${p.excelEmployeeId ?? ""}`] !== false),
    [unmatched, selected],
  );
  const monthlyTotals = useMemo(() => {
    if (!report) return null;
    const days = report.employees.flatMap((emp) => emp.dailyEntries ?? []);
    return {
      ...aggregateAttendanceTotals(days, report.latesPerOff),
      employeeCount: report.employees.length,
    };
  }, [report]);

  async function runAnalyze(file: File) {
    if (saturdayOffMode === "date") {
      if (!saturdayOffDate) {
        setError("Pick the Saturday off date on the calendar, or choose Recommended / Don't know.");
        return;
      }
      if (!isSaturdayIso(saturdayOffDate)) {
        setError("The calendar date must be a Saturday.");
        return;
      }
    }
    setError(null);
    setInfo(null);
    setReport(null);
    setExpanded(null);
    try {
      const res = await analyze.mutateAsync({
        file,
        saturdayOffMode,
        saturdayOffDate: saturdayOffMode === "date" ? saturdayOffDate : null,
      });
      setReport(res);
      const next: Record<string, boolean> = {};
      for (const p of res.unmatchedPeople ?? []) {
        next[`${p.fullName}|${p.excelEmployeeId ?? ""}`] = true;
      }
      setSelected(next);
      const offs = res.saturdayOffDates ?? [];
      if (offs.length > 0) {
        setInfo(`Saturday off treated as holiday (not absent): ${offs.join(", ")}.`);
      } else if (saturdayOffMode === "auto") {
        setInfo("Don't know: no clear Saturday off was detected from this file.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    }
  }

  async function onUpload(files: FileList | null) {
    if (!files?.[0]) return;
    lastFileRef.current = files[0];
    await runAnalyze(files[0]);
  }

  async function onAddEmployees() {
    if (selectedPeople.length === 0) return;
    setError(null);
    setInfo(null);
    try {
      const res = await addEmployees.mutateAsync(selectedPeople);
      const skipNote = res.skipped.length ? ` Skipped: ${res.skipped.join("; ")}` : "";
      setInfo(
        `Added ${res.created} employee(s) with Excel IDs as employee codes.${skipNote} Re-upload the same file to save their attendance.`,
      );
      const file = lastFileRef.current;
      if (file && res.created > 0) {
        await runAnalyze(file);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add employees");
    }
  }

  const radioStyle = {
    display: "grid",
    gap: "var(--space-2)",
    margin: 0,
  } as const;

  const optionRow = {
    display: "flex",
    gap: "var(--space-3)",
    alignItems: "center",
    flexWrap: "wrap" as const,
    padding: "var(--space-3)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    background: "var(--color-surface)",
  };

  return (
    <>
      <PageHeader
        title="Import Excel file for attendance"
        breadcrumb="Attendance / Import Excel"
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
            Upload the WebHR attendance export (
            <strong>Employee ID</strong>, <strong>First Name</strong>, <strong>Date</strong>,{" "}
            <strong>First Punch</strong>). Late and half-day count as <strong>present</strong>. Sundays
            are official off. Tell us which <strong>Saturday is off</strong> below so that day is a
            holiday, not absent. Anyone who punched that day gets +1 OT. 3 lates = 1 extra absent day.
          </p>

          <fieldset style={{ border: 0, padding: 0, margin: "0 0 var(--space-4)" }}>
            <legend
              style={{
                fontSize: "var(--text-sm)",
                fontWeight: "var(--weight-semibold)",
                color: "var(--color-text-secondary)",
                marginBottom: "var(--space-2)",
              }}
            >
              When is the Saturday off?
            </legend>
            <div style={radioStyle}>
              <label
                style={{
                  ...optionRow,
                  borderColor:
                    saturdayOffMode === "second_saturday"
                      ? "var(--color-accent)"
                      : "var(--color-border)",
                  background:
                    saturdayOffMode === "second_saturday"
                      ? "var(--color-accent-subtle)"
                      : "var(--color-surface)",
                }}
              >
                <input
                  type="radio"
                  name="saturday-off"
                  checked={saturdayOffMode === "second_saturday"}
                  onChange={() => setSaturdayOffMode("second_saturday")}
                />
                <span>
                  Second Saturday of the month{" "}
                  <span
                    style={{
                      marginLeft: "var(--space-2)",
                      fontSize: "var(--text-xs)",
                      fontWeight: "var(--weight-semibold)",
                      letterSpacing: "0.02em",
                      textTransform: "uppercase",
                      color: "var(--color-status-positive)",
                      background: "var(--color-status-positive-bg)",
                      padding: "2px 8px",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    Recommended
                  </span>
                </span>
              </label>

              <label
                style={{
                  ...optionRow,
                  borderColor:
                    saturdayOffMode === "date" ? "var(--color-accent)" : "var(--color-border)",
                  background:
                    saturdayOffMode === "date"
                      ? "var(--color-accent-subtle)"
                      : "var(--color-surface)",
                }}
              >
                <input
                  type="radio"
                  name="saturday-off"
                  checked={saturdayOffMode === "date"}
                  onChange={() => setSaturdayOffMode("date")}
                />
                <span style={{ minWidth: 120 }}>Pick a Saturday</span>
                <input
                  className="form-field__input"
                  type="date"
                  value={saturdayOffDate}
                  onChange={(e) => {
                    setSaturdayOffDate(e.target.value);
                    setSaturdayOffMode("date");
                  }}
                  onFocus={() => setSaturdayOffMode("date")}
                  style={{ maxWidth: 200 }}
                />
                {saturdayOffDate && !isSaturdayIso(saturdayOffDate) ? (
                  <span style={{ color: "var(--color-status-critical)", fontSize: "var(--text-sm)" }}>
                    Must be a Saturday
                  </span>
                ) : null}
              </label>

              <label
                style={{
                  ...optionRow,
                  borderColor:
                    saturdayOffMode === "auto" ? "var(--color-accent)" : "var(--color-border)",
                  background:
                    saturdayOffMode === "auto"
                      ? "var(--color-accent-subtle)"
                      : "var(--color-surface)",
                }}
              >
                <input
                  type="radio"
                  name="saturday-off"
                  checked={saturdayOffMode === "auto"}
                  onChange={() => setSaturdayOffMode("auto")}
                />
                <span>Don&apos;t know — detect automatically with AI</span>
              </label>
            </div>
          </fieldset>

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
        {info ? <p style={{ color: "var(--color-status-info)", margin: 0 }}>{info}</p> : null}
        {analyze.isPending ? <Spinner label="Processing attendance file" /> : null}

        {report && unmatched.length > 0 ? (
          <Card status="warning">
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>New names in this file</h2>
            <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              These people are not in Employees yet. Add them to create a record with the Excel
              Employee ID as their ID. You can fill salary and other details later.
            </p>
            <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
              {unmatched.map((p) => {
                const key = `${p.fullName}|${p.excelEmployeeId ?? ""}`;
                return (
                  <li key={key} style={{ marginBottom: "var(--space-2)" }}>
                    <label style={{ display: "inline-flex", gap: "var(--space-2)", alignItems: "center" }}>
                      <input
                        type="checkbox"
                        checked={selected[key] !== false}
                        onChange={(e) => setSelected((prev) => ({ ...prev, [key]: e.target.checked }))}
                      />
                      <span>
                        {p.fullName}
                        {p.excelEmployeeId ? (
                          <>
                            {" "}
                            — ID <span className="num">{p.excelEmployeeId}</span>
                          </>
                        ) : (
                          " — no Excel ID"
                        )}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
            <div style={{ marginTop: "var(--space-3)" }}>
              <Button
                type="button"
                variant="primary"
                disabled={addEmployees.isPending || selectedPeople.length === 0}
                onClick={() => void onAddEmployees()}
              >
                {addEmployees.isPending
                  ? "Adding…"
                  : `Add ${selectedPeople.length} employee${selectedPeople.length === 1 ? "" : "s"}`}
              </Button>
            </div>
          </Card>
        ) : null}

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
                <span className="num">{report.latesPerOff}</span> lates = 1 absent
                {" · "}month days <span className="num">{report.monthDays}</span>
                {" · "}imported <span className="num">{report.importedRows}</span> rows
              </p>
              {(report.saturdayOffDates ?? []).length > 0 ? (
                <p style={{ margin: "var(--space-2) 0 0" }}>
                  Saturday off (holiday, not absent):{" "}
                  <span className="num">{(report.saturdayOffDates ?? []).join(", ")}</span>
                </p>
              ) : null}
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
                  No Sunday / Saturday-off / company-off days detected in this file.
                </p>
              )}
            </Card>

            <section className="card">
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "var(--space-3)",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "var(--space-4)",
                }}
              >
                <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Employee attendance</h2>
                <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                  <Button
                    type="button"
                    variant={reportView === "summary" ? "primary" : "secondary"}
                    onClick={() => setReportView("summary")}
                  >
                    Summary table
                  </Button>
                  <Button
                    type="button"
                    variant={reportView === "monthly" ? "primary" : "secondary"}
                    onClick={() => setReportView("monthly")}
                  >
                    Monthly grid
                  </Button>
                </div>
              </div>

              {reportView === "monthly" && monthlyTotals ? (
                <MonthlyAttendanceGrid
                  periodStart={report.periodStart}
                  periodEnd={report.periodEnd}
                  totals={monthlyTotals}
                />
              ) : reportView === "summary" ? (
                <Table
                  headers={[
                    "Employee",
                    "Present",
                    "Late",
                    "Half day",
                    "Sunday",
                    "Absent",
                    "OT",
                    "Est. net",
                    "Details",
                  ]}
                >
                  {report.employees.map((emp) => (
                    <Fragment key={`${emp.fullName}-${emp.excelEmployeeId ?? emp.employeeId ?? ""}`}>
                      <tr data-status={emp.daysAbsent > 0 ? "warning" : "positive"}>
                        <td>
                          <div>{emp.fullName}</div>
                          <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                            {emp.matchedEmployee
                              ? emp.employeeCode || "Linked employee"
                              : "Not in Employees yet"}
                          </div>
                        </td>
                        <td className="num">{emp.daysPresent}</td>
                        <td className="num">{emp.daysLate}</td>
                        <td className="num">{emp.daysHalfDay}</td>
                        <td className="num">{emp.daysSundayPresent}</td>
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
                          <td colSpan={9}>
                            <EmployeeDetail emp={emp} />
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  ))}
                </Table>
              ) : null}
            </section>
          </>
        ) : null}
      </div>
    </>
  );
}
