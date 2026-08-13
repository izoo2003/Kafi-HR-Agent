import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { StatusBadge } from "../../components/ui/Badge";
import { Pagination } from "../../components/ui/Pagination";
import { usePayrollSalaries, useUpdatePayrollSalary } from "../../hooks/usePayroll";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import { ApiError } from "../../api/client";
import type { PayrollSalaryRow } from "../../types/payroll";

function SalaryRow({
  row,
  canEdit,
}: {
  row: PayrollSalaryRow;
  canEdit: boolean;
}) {
  const update = useUpdatePayrollSalary();
  const [value, setValue] = useState(row.baseSalary != null ? String(row.baseSalary) : "");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setValue(row.baseSalary != null ? String(row.baseSalary) : "");
  }, [row.baseSalary]);

  const original = row.baseSalary != null ? String(row.baseSalary) : "";
  const dirty = value.trim() !== original;

  async function save() {
    setError(null);
    setMessage(null);
    const trimmed = value.trim();
    let baseSalary: number | null = null;
    if (trimmed !== "") {
      const n = Number(trimmed);
      if (!Number.isFinite(n) || n < 0) {
        setError("Enter a valid non-negative salary");
        return;
      }
      baseSalary = n;
    }
    try {
      await update.mutateAsync({ employeeId: row.employeeId, payload: { baseSalary } });
      setMessage("Saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    }
  }

  return (
    <tr data-status="positive">
      <td>
        <div>{row.fullName}</div>
        <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
          {row.employeeCode}
        </div>
      </td>
      <td>{row.departmentName ?? `#${row.departmentId}`}</td>
      <td>{row.roleTitle}</td>
      <td>
        <StatusBadge status="approved">Active</StatusBadge>
      </td>
      <td>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap" }}>
          <input
            className="form-field__input font-data"
            type="number"
            min={0}
            step="0.01"
            disabled={!canEdit}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            style={{ width: 140 }}
            aria-label={`Salary for ${row.fullName}`}
          />
          {canEdit ? (
            <Button
              type="button"
              variant="primary"
              disabled={!dirty || update.isPending}
              onClick={save}
            >
              {update.isPending ? "Saving…" : "Save"}
            </Button>
          ) : null}
        </div>
        {error ? (
          <div style={{ color: "var(--color-status-critical)", fontSize: "var(--text-xs)" }}>{error}</div>
        ) : null}
        {message ? (
          <div style={{ color: "var(--color-status-positive)", fontSize: "var(--text-xs)" }}>{message}</div>
        ) : null}
      </td>
    </tr>
  );
}

/** Payroll landing — active employees and editable base salaries. */
export function PayrollRunListPage() {
  const { hasPermission } = useAuth();
  const canEdit = hasPermission("payroll", "write");
  const { page, pageSize, setPage, params } = usePagination();
  const salaries = usePayrollSalaries(params);

  return (
    <>
      <PageHeader
        title="Payroll"
        breadcrumb="Payroll"
        actions={
          <>
            <Link to="/payroll/compute">
              <Button variant="primary">Salary calculation</Button>
            </Link>
            <Link to="/payroll/tax-slabs">
              <Button variant="secondary">Tax slabs</Button>
            </Link>
          </>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-4)" }}>
        <p style={{ margin: 0, color: "var(--color-text-muted)" }}>
          Set each employee&apos;s base salary here. Net pay (attendance + tax) is on Salary
          calculation; tax years/slabs (including 2026-27) are editable under Tax slabs.
        </p>

        {salaries.isLoading ? <Spinner label="Loading salaries" /> : null}

        {!salaries.isLoading && (salaries.data?.total ?? 0) === 0 ? (
          <EmptyState
            title="No active employees"
            description="Add active employees in the Employees section first. Their salaries will appear here for payroll."
            actionLabel="Go to Employees"
            onAction={() => {
              window.location.href = "/employees";
            }}
          />
        ) : null}

        {salaries.data && salaries.data.items.length > 0 ? (
          <>
            <Table headers={["Employee", "Department", "Role", "Status", "Base salary"]}>
              {salaries.data.items.map((row) => (
                <SalaryRow key={row.employeeId} row={row} canEdit={canEdit} />
              ))}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={salaries.data.total}
              onPageChange={setPage}
            />
          </>
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
