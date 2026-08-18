import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { usePayrollCompute, useTaxYears } from "../../hooks/usePayroll";

function money(n: string | number | null | undefined): string {
  if (n == null || n === "") return "—";
  return Number(n).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function monthLabel(month: number, year: number): string {
  return `${new Date(2000, month - 1, 1).toLocaleString("en", { month: "long" })} ${year}`;
}

/** Payroll landing — name, base salary, and this month's net payable. */
export function PayrollRunListPage() {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const taxYears = useTaxYears();

  const activeTaxId = useMemo(() => {
    const active = (taxYears.data ?? []).find((y) => y.isActive) ?? taxYears.data?.[0];
    return active?.id ?? "";
  }, [taxYears.data]);

  const compute = usePayrollCompute(
    activeTaxId === ""
      ? null
      : { periodMonth: month, periodYear: year, taxYearId: Number(activeTaxId) },
  );

  const rows = compute.data?.employees ?? [];

  return (
    <>
      <PageHeader
        title="Payroll"
        breadcrumb="Payroll"
        actions={
          <>
            <Link to="/payroll/compute">
              <Button variant="primary">Edit Salary Sheets</Button>
            </Link>
            <Link to="/payroll/compute">
              <Button variant="secondary">Salary calculation</Button>
            </Link>
            <Link to="/payroll/tax-slabs">
              <Button variant="secondary">Tax slabs</Button>
            </Link>
          </>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-4)" }}>
        <p style={{ margin: 0, color: "var(--color-text-muted)" }}>
          Base salary and net payable for {monthLabel(month, year)}. Open Edit Salary Sheets for the
          full Excel salary-sheet layout.
        </p>
        <div
          style={{
            display: "grid",
            gap: "var(--space-3)",
            gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
            maxWidth: 420,
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
        </div>

        {compute.isLoading || taxYears.isLoading ? <Spinner label="Loading salaries" /> : null}

        {compute.isError ? (
          <p style={{ color: "var(--color-status-critical)" }}>
            Could not calculate net salary for this month. Check tax slabs, then open Salary
            calculation.
          </p>
        ) : null}

        {!compute.isLoading && !compute.isError && rows.length === 0 ? (
          <EmptyState
            title="No active employees"
            description="Add active employees in the Employees section first. Their salaries will appear here for payroll."
            actionLabel="Go to Employees"
            onAction={() => {
              window.location.href = "/employees";
            }}
          />
        ) : null}

        {rows.length > 0 ? (
          <Table headers={["Employee", "Base salary", "Net salary"]}>
            {rows.map((row) => (
              <tr key={row.employeeId} data-status="positive">
                <td>
                  <div>{row.fullName}</div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                    {row.employeeCode}
                  </div>
                </td>
                <td className="num">{money(row.baseSalary)}</td>
                <td className="num">{money(row.netPayable ?? row.netSalary)}</td>
              </tr>
            ))}
          </Table>
        ) : null}
      </div>
    </>
  );
}

export function PayrollRunDetailPage() {
  return (
    <>
      <PageHeader title="Payroll Run" breadcrumb="Payroll / Runs / Detail" />
      <div className="page">
        <EmptyState title="Run detail" description="Payslip list and approval actions pending." />
      </div>
    </>
  );
}

export function PayslipDetailPage() {
  return (
    <>
      <PageHeader title="Payslip" breadcrumb="Payroll / Payslip" />
      <div className="page">
        <EmptyState title="Payslip" description="Line items and PDF download pending." />
      </div>
    </>
  );
}

export function SalaryAdvancesPage() {
  return (
    <>
      <PageHeader title="Salary Advances" breadcrumb="Payroll / Advances" />
      <div className="page">
        <EmptyState title="Advances" description="Advance request and recovery tracking pending." />
      </div>
    </>
  );
}
