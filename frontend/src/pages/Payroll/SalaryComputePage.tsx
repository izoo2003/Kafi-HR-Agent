import { Fragment, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { usePayrollCompute, useTaxYears } from "../../hooks/usePayroll";

function money(n: string | number | null | undefined): string {
  if (n == null || n === "") return "—";
  return Number(n).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function SalaryComputePage() {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const taxYears = useTaxYears();
  const [taxYearId, setTaxYearId] = useState<number | "">("");
  const [expanded, setExpanded] = useState<number | null>(null);

  const activeTaxId = useMemo(() => {
    if (taxYearId !== "") return taxYearId;
    const active = (taxYears.data ?? []).find((y) => y.isActive) ?? taxYears.data?.[0];
    return active?.id ?? "";
  }, [taxYearId, taxYears.data]);

  const compute = usePayrollCompute(
    activeTaxId === ""
      ? null
      : { periodMonth: month, periodYear: year, taxYearId: Number(activeTaxId) },
  );

  return (
    <>
      <PageHeader
        title="Salary calculation"
        breadcrumb="Payroll / Salary calculation"
        actions={
          <>
            <Link to="/payroll/tax-slabs">
              <Button variant="secondary">Tax slabs</Button>
            </Link>
            <Link to="/attendance/period-report">
              <Button variant="secondary">Attendance Excel</Button>
            </Link>
          </>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <Card>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Net salary = base − (absents × base/30) − (late-offs × base/30) − (half-days × base/60) +
            OT days − monthly tax. Late after 09:40; after 11:30 = late + half day; 3 lates = 1 off.
            Upload attendance via Attendance → Excel period report first.
          </p>
          <div
            style={{
              display: "grid",
              gap: "var(--space-3)",
              gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
              maxWidth: 720,
            }}
          >
            <label className="form-field">
              <span className="form-field__label">Month</span>
              <select
                className="form-field__input"
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
              >
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {new Date(2000, i, 1).toLocaleString("en", { month: "long" })}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span className="form-field__label">Year</span>
              <input
                className="form-field__input font-data"
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              />
            </label>
            <label className="form-field">
              <span className="form-field__label">Tax year</span>
              <select
                className="form-field__input"
                value={activeTaxId === "" ? "" : String(activeTaxId)}
                onChange={(e) => setTaxYearId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Select…</option>
                {(taxYears.data ?? []).map((y) => (
                  <option key={y.id} value={y.id}>
                    {y.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </Card>

        {compute.isLoading ? <Spinner label="Calculating salaries" /> : null}
        {compute.isError ? (
          <p style={{ color: "var(--color-status-critical)" }}>Could not compute payroll.</p>
        ) : null}

        {compute.data ? (
          <>
            <Card>
              <strong>
                {compute.data.periodStart} → {compute.data.periodEnd}
              </strong>
              {" · "}tax {compute.data.taxYearLabel}
              {" · "}month days {compute.data.monthDays}
            </Card>
            <Table
              headers={[
                "Employee",
                "Base",
                "Absent",
                "Late",
                "Half",
                "Late offs",
                "Gross",
                "Monthly tax",
                "Net salary",
                "",
              ]}
            >
              {compute.data.employees.map((e) => (
                <Fragment key={e.employeeId}>
                  <tr data-status="positive">
                    <td>
                      <div>{e.fullName}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                        {e.employeeCode}
                      </div>
                    </td>
                    <td className="num">{money(e.baseSalary)}</td>
                    <td className="num">{e.daysAbsent}</td>
                    <td className="num">{e.daysLate}</td>
                    <td className="num">{e.daysHalfDay}</td>
                    <td className="num">{e.lateOffDays}</td>
                    <td className="num">{money(e.grossAfterAttendance)}</td>
                    <td className="num">{money(e.monthlyTax)}</td>
                    <td className="num">{money(e.netSalary)}</td>
                    <td>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          setExpanded(expanded === e.employeeId ? null : e.employeeId)
                        }
                      >
                        {expanded === e.employeeId ? "Hide" : "Details"}
                      </Button>
                    </td>
                  </tr>
                  {expanded === e.employeeId ? (
                    <tr>
                      <td colSpan={10}>
                        <div
                          style={{
                            display: "grid",
                            gap: 6,
                            padding: "var(--space-3)",
                            background: "var(--color-surface-alt)",
                            borderRadius: "var(--radius-md)",
                            fontSize: "var(--text-sm)",
                          }}
                        >
                          <div>
                            Per day (base/30): <span className="num">{money(e.perDayRate)}</span>
                          </div>
                          <div>
                            Attendance deduction:{" "}
                            <span className="num">{money(e.attendanceDeduction)}</span>
                            {" · "}OT: <span className="num">{money(e.overtimeAmount)}</span>
                            {" · "}leave used {e.leaveUsed}/{e.leaveAllowance}
                          </div>
                          <div>
                            Annual taxable: <span className="num">{money(e.annualTaxableIncome)}</span>
                            {" · "}annual tax: <span className="num">{money(e.annualTax)}</span>
                          </div>
                          {e.lateEvents.length > 0 ? (
                            <div>
                              Late events:{" "}
                              {e.lateEvents
                                .map((x) => `${x.date} ${x.checkInTime}${x.note ? ` (${x.note})` : ""}`)
                                .join("; ")}
                            </div>
                          ) : null}
                          {e.notes ? (
                            <div style={{ color: "var(--color-status-warning)" }}>{e.notes}</div>
                          ) : null}
                        </div>
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
