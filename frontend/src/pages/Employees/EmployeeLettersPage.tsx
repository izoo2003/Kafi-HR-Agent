import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { StatusBadge } from "../../components/ui/Badge";
import { Pagination } from "../../components/ui/Pagination";
import { useAuth } from "../../hooks/useAuth";
import { useDepartments, useEmployees } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { createEmployeeLetter, viewEmployeeLetter } from "../../api/employees";
import { ApiError } from "../../api/client";
import type { Employee } from "../../types/employees";

type LetterKind = "appointment" | "contract";

const COPY: Record<
  LetterKind,
  { title: string; breadcrumb: string; file: string; empty: string; createLabel: string }
> = {
  appointment: {
    title: "Appointment letters",
    breadcrumb: "Organization / Employees / Appointment letter",
    file: "Appointment_Letter",
    empty: "No employees yet. Add an employee first, then create their appointment letter here.",
    createLabel: "Create appointment letter",
  },
  contract: {
    title: "Contract letters",
    breadcrumb: "Organization / Employees / Contract letter",
    file: "Employment_Contract",
    empty: "No employees yet. Add an employee first, then create their contract letter here.",
    createLabel: "Create contract letter",
  },
};

function hasLetter(emp: Employee, kind: LetterKind): boolean {
  return kind === "appointment" ? Boolean(emp.hasAppointmentLetter) : Boolean(emp.hasContractLetter);
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function fileName(kind: LetterKind, emp: Employee) {
  const safe = emp.fullName.replace(/[^\w\-]+/g, "_");
  return `${COPY[kind].file}_${safe}.docx`;
}

export function EmployeeLettersPage({ kind }: { kind: LetterKind }) {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const { page, pageSize, setPage, params } = usePagination(1, 100);
  const [statusFilter, setStatusFilter] = useState<"active" | "terminated" | "all">("active");
  const departments = useDepartments();
  const employees = useEmployees({
    ...params,
    status: statusFilter === "all" ? undefined : statusFilter,
  });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const copy = COPY[kind];

  const deptNameById = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  async function onCreate(emp: Employee) {
    setError(null);
    setMessage(null);
    setBusyId(emp.id);
    try {
      const blob = await createEmployeeLetter(emp.id, kind);
      downloadBlob(blob, fileName(kind, emp));
      setMessage(`${copy.createLabel} created for ${emp.fullName}.`);
      await employees.refetch();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not create the letter.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function onView(emp: Employee) {
    if (!hasLetter(emp, kind)) {
      setError("It is not created yet. Create them first.");
      return;
    }
    setError(null);
    setBusyId(emp.id);
    try {
      const blob = await viewEmployeeLetter(emp.id, kind);
      downloadBlob(blob, fileName(kind, emp));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "It is not created yet. Create them first.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader title={copy.title} breadcrumb={copy.breadcrumb} />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Select an employee to create or view their {kind === "appointment" ? "appointment letter" : "contract letter"}.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        <label className="form-field" style={{ maxWidth: 220 }}>
          <span className="form-field__label">Show</span>
          <select
            className="form-field__input"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as "active" | "terminated" | "all");
              setPage(1);
            }}
          >
            <option value="active">Active only</option>
            <option value="terminated">Terminated only</option>
            <option value="all">All</option>
          </select>
        </label>

        {employees.isLoading ? <Spinner label="Loading employees" /> : null}
        {employees.data && employees.data.items.length === 0 ? (
          <EmptyState title="No employees found" description={copy.empty} />
        ) : null}
        {employees.data && employees.data.items.length > 0 ? (
          <>
            <Table headers={["Code", "Name", "Role", "Letter", "Actions"]}>
              {employees.data.items.map((emp) => {
                const created = hasLetter(emp, kind);
                const busy = busyId === emp.id;
                return (
                  <tr key={emp.id} data-status={created ? "positive" : "neutral"}>
                    <td className="num">{emp.employeeCode}</td>
                    <td>{emp.fullName}</td>
                    <td>{deptNameById(emp.departmentId)}</td>
                    <td>
                      <StatusBadge status={created ? "approved" : "draft"}>
                        {created ? "Created" : "Not created"}
                      </StatusBadge>
                    </td>
                    <td className="col-actions">
                      <div className="table-actions" style={{ justifyContent: "flex-end" }}>
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={busy || !created}
                          onClick={() => void onView(emp)}
                        >
                          View letter
                        </Button>
                        {canWrite ? (
                          <Button
                            type="button"
                            variant="primary"
                            disabled={busy || emp.status === "terminated"}
                            onClick={() => void onCreate(emp)}
                          >
                            {busy ? "Working…" : created ? "Recreate letter" : copy.createLabel}
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={employees.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}

        <div>
          <Link to="/employees">
            <Button type="button" variant="secondary">
              Back to employees
            </Button>
          </Link>
        </div>
      </div>
    </>
  );
}
