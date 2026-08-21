import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { StatusBadge } from "../../components/ui/Badge";
import { Pagination } from "../../components/ui/Pagination";
import {
  useDepartments,
  useEmployees,
  useExitEmployee,
  useUpdateEmployee,
} from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import { ApiError } from "../../api/client";
import type { Employee, EmployeeLocation } from "../../types/employees";
import { EMPLOYEE_LOCATIONS } from "../../types/employees";

export function EmployeeListPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const { page, pageSize, setPage, params } = usePagination();
  const [statusFilter, setStatusFilter] = useState<"active" | "terminated" | "all">("active");
  const departments = useDepartments();
  const employees = useEmployees({
    ...params,
    status: statusFilter === "all" ? undefined : statusFilter,
  });
  const exitEmp = useExitEmployee();
  const updateEmp = useUpdateEmployee();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [savingLocationId, setSavingLocationId] = useState<number | null>(null);

  const deptNameById = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  async function onExit(emp: Employee) {
    if (emp.status === "terminated") return;
    const ok = window.confirm(
      `Remove ${emp.fullName} (${emp.employeeCode}) from the active roster?\n\nThey will be marked terminated (not hard-deleted) so attendance/KPI history stays intact.`,
    );
    if (!ok) return;
    setError(null);
    setMessage(null);
    try {
      await exitEmp.mutateAsync(emp.id);
      setMessage(`${emp.fullName} removed from active employees`);
      setPage(1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove employee");
    }
  }

  async function onLocationChange(emp: Employee, value: string) {
    const next = (value.trim() || null) as EmployeeLocation | null;
    if ((emp.location ?? null) === next) return;
    setError(null);
    setMessage(null);
    setSavingLocationId(emp.id);
    try {
      await updateEmp.mutateAsync({ id: emp.id, payload: { location: next } });
      setMessage(`Location updated for ${emp.fullName}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update location");
    } finally {
      setSavingLocationId(null);
    }
  }

  return (
    <>
      <PageHeader title="Employees" breadcrumb="Organization / Employees" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        <div
          style={{
            display: "flex",
            gap: "var(--space-3)",
            alignItems: "end",
            flexWrap: "wrap",
            justifyContent: "space-between",
          }}
        >
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
          {canWrite ? (
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              <Link to="/employees/verify-cnic">
                <Button type="button" variant="secondary">
                  Verify my CNIC
                </Button>
              </Link>
              <Link to="/employees/new">
                <Button type="button" variant="primary">
                  Add Employee
                </Button>
              </Link>
            </div>
          ) : null}
        </div>

        {employees.isLoading ? <Spinner label="Loading employees" /> : null}
        {employees.data && employees.data.items.length === 0 ? (
          <EmptyState
            title={statusFilter === "active" ? "No active employees" : "No employees found"}
            description={
              statusFilter === "active"
                ? "Add an employee to start building the roster, or switch the filter to see terminated records."
                : "Open Employees, expand the menu, then use Departments to create a department before adding an employee."
            }
          />
        ) : null}
        {employees.data && employees.data.items.length > 0 ? (
          <>
            <Table
              headers={[
                "Code",
                "Name",
                "CNIC",
                "Department",
                "Location",
                "Mobile",
                "Status",
                "Base salary",
                "Actions",
              ]}
            >
              {employees.data.items.map((e) => (
                <tr key={e.id} data-status={e.status === "active" ? "positive" : "neutral"}>
                  <td className="num">{e.employeeCode}</td>
                  <td>
                    <Link to={`/employees/${e.id}`} style={{ color: "var(--color-accent)" }}>
                      {e.fullName}
                    </Link>
                  </td>
                  <td className="num">{e.cnic ?? "—"}</td>
                  <td>{deptNameById(e.departmentId)}</td>
                  <td>
                    {canWrite && e.status !== "terminated" ? (
                      <select
                        className="form-field__input"
                        value={e.location ?? ""}
                        onChange={(ev) => onLocationChange(e, ev.target.value)}
                        disabled={savingLocationId === e.id || updateEmp.isPending}
                        aria-label={`Location for ${e.fullName}`}
                        style={{ minWidth: 140 }}
                      >
                        <option value="">Select…</option>
                        {EMPLOYEE_LOCATIONS.map((loc) => (
                          <option key={loc} value={loc}>
                            {loc}
                          </option>
                        ))}
                      </select>
                    ) : (
                      e.location ?? "—"
                    )}
                  </td>
                  <td className="num">{e.personalMobile ?? "—"}</td>
                  <td>
                    <StatusBadge status={e.status === "active" ? "approved" : "draft"}>
                      {e.status}
                    </StatusBadge>
                  </td>
                  <td className="num">{e.baseSalary ?? "—"}</td>
                  <td className="col-actions">
                    <div className="table-actions" style={{ justifyContent: "flex-end" }}>
                      {canWrite ? (
                        <>
                          <Link to={`/employees/${e.id}?mode=view`}>
                            <Button type="button" variant="secondary">
                              View
                            </Button>
                          </Link>
                          <Link to={`/employees/${e.id}`}>
                            <Button type="button" variant="primary" disabled={e.status === "terminated"}>
                              Edit
                            </Button>
                          </Link>
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={() => onExit(e)}
                            disabled={e.status === "terminated" || exitEmp.isPending}
                          >
                            Delete
                          </Button>
                        </>
                      ) : (
                        <Link to={`/employees/${e.id}?mode=view`}>
                          <Button type="button" variant="secondary">
                            View
                          </Button>
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={employees.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
    </>
  );
}
