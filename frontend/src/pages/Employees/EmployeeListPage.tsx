import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { StatusBadge } from "../../components/ui/Badge";
import { Pagination } from "../../components/ui/Pagination";
import {
  useCreateDepartment,
  useDepartments,
  useEmployees,
  useExitEmployee,
} from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import { ApiError } from "../../api/client";
import type { Employee } from "../../types/employees";

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
  const createDept = useCreateDepartment();
  const exitEmp = useExitEmployee();

  const [deptName, setDeptName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const deptNameById = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  async function onCreateDept(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createDept.mutateAsync({ name: deptName.trim() });
      setDeptName("");
      setMessage("Department added — it will appear in the employee Role dropdown.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create department");
    }
  }

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

  return (
    <>
      <PageHeader title="Employees" breadcrumb="Organization / Employees" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        <section className="card">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: "var(--space-3)",
              flexWrap: "wrap",
              alignItems: "center",
              marginBottom: "var(--space-4)",
            }}
          >
            <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Departments (roles)</h2>
            {canWrite ? (
              <Link to="/employees/new">
                <Button type="button" variant="primary">
                  Add Employee
                </Button>
              </Link>
            ) : null}
          </div>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Departments are used as selectable roles when creating or editing an employee.
          </p>
          {canWrite ? (
            <form
              onSubmit={onCreateDept}
              style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-4)" }}
            >
              <FormField
                label="New department / role"
                value={deptName}
                onChange={(e) => setDeptName(e.target.value)}
                required
              />
              <div style={{ alignSelf: "end" }}>
                <Button type="submit" variant="secondary">
                  Add Department
                </Button>
              </div>
            </form>
          ) : null}
          {departments.isLoading ? <Spinner /> : null}
          <ul
            style={{
              margin: 0,
              paddingLeft: "1.2rem",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: "var(--space-1)",
            }}
          >
            {(departments.data ?? []).map((d) => (
              <li key={d.id}>{d.name}</li>
            ))}
          </ul>
        </section>

        <div
          style={{
            display: "flex",
            gap: "var(--space-3)",
            alignItems: "end",
            flexWrap: "wrap",
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
        </div>

        {employees.isLoading ? <Spinner label="Loading employees" /> : null}
        {employees.data && employees.data.items.length === 0 ? (
          <EmptyState
            title={statusFilter === "active" ? "No active employees" : "No employees found"}
            description={
              statusFilter === "active"
                ? "Add an employee to start building the roster, or switch the filter to see terminated records."
                : "Create a department, then add your first employee record."
            }
          />
        ) : null}
        {employees.data && employees.data.items.length > 0 ? (
          <>
            <Table
              headers={
                canWrite
                  ? ["Code", "Name", "CNIC", "Role", "Mobile", "Status", "Base salary", "Actions"]
                  : ["Code", "Name", "CNIC", "Role", "Mobile", "Status", "Base salary"]
              }
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
                  <td className="num">{e.personalMobile ?? "—"}</td>
                  <td>
                    <StatusBadge status={e.status === "active" ? "approved" : "draft"}>
                      {e.status}
                    </StatusBadge>
                  </td>
                  <td className="num">{e.baseSalary ?? "—"}</td>
                  {canWrite ? (
                    <td>
                      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                        <Link to={`/employees/${e.id}`}>
                          <Button type="button" variant="secondary">
                            Open
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
                      </div>
                    </td>
                  ) : null}
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
