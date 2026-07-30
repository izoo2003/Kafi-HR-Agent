import { useMemo, useState, type FormEvent } from "react";
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
  useCreateEmployee,
  useDepartments,
  useEmployees,
  useExitEmployee,
  useUpdateEmployee,
} from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import { ApiError } from "../../api/client";
import type { Employee } from "../../types/employees";

const emptyForm = {
  employeeCode: "",
  fullName: "",
  departmentId: "",
  roleTitle: "",
  baseSalary: "",
};

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
  const createEmp = useCreateEmployee();
  const updateEmp = useUpdateEmployee();
  const exitEmp = useExitEmployee();

  const [deptName, setDeptName] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const deptNameById = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  function startEdit(emp: Employee) {
    setEditingId(emp.id);
    setError(null);
    setMessage(null);
    setForm({
      employeeCode: emp.employeeCode,
      fullName: emp.fullName,
      departmentId: String(emp.departmentId),
      roleTitle: emp.roleTitle,
      baseSalary: emp.baseSalary != null ? String(emp.baseSalary) : "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function onCreateDept(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createDept.mutateAsync({ name: deptName.trim() });
      setDeptName("");
      setMessage("Department added");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create department");
    }
  }

  async function onSaveEmployee(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      if (editingId != null) {
        await updateEmp.mutateAsync({
          id: editingId,
          payload: {
            fullName: form.fullName.trim(),
            departmentId: Number(form.departmentId),
            roleTitle: form.roleTitle.trim(),
            baseSalary: form.baseSalary ? Number(form.baseSalary) : null,
          },
        });
        setMessage("Employee updated");
        cancelEdit();
      } else {
        await createEmp.mutateAsync({
          employeeCode: form.employeeCode.trim(),
          fullName: form.fullName.trim(),
          departmentId: Number(form.departmentId),
          roleTitle: form.roleTitle.trim(),
          baseSalary: form.baseSalary ? Number(form.baseSalary) : undefined,
        });
        setForm({ ...emptyForm, departmentId: form.departmentId });
        setMessage("Employee created");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save employee");
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
      if (editingId === emp.id) cancelEdit();
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
          <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Departments</h2>
          {canWrite ? (
            <form
              onSubmit={onCreateDept}
              style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-4)" }}
            >
              <FormField
                label="New department"
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

        {canWrite ? (
          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>
              {editingId != null ? "Edit employee" : "Add employee"}
            </h2>
            <form
              onSubmit={onSaveEmployee}
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
              }}
            >
              <FormField
                label="Employee code"
                value={form.employeeCode}
                onChange={(e) => setForm({ ...form, employeeCode: e.target.value })}
                required
                disabled={editingId != null}
                hint={editingId != null ? "Code cannot be changed after create" : undefined}
              />
              <FormField
                label="Full name"
                value={form.fullName}
                onChange={(e) => setForm({ ...form, fullName: e.target.value })}
                required
              />
              <label className="form-field">
                <span className="form-field__label">Department</span>
                <select
                  className="form-field__input"
                  value={form.departmentId}
                  onChange={(e) => setForm({ ...form, departmentId: e.target.value })}
                  required
                >
                  <option value="">Select…</option>
                  {(departments.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <FormField
                label="Role title"
                value={form.roleTitle}
                onChange={(e) => setForm({ ...form, roleTitle: e.target.value })}
                required
              />
              <FormField
                label="Base salary"
                type="number"
                min="0"
                max="9999999999.99"
                step="0.01"
                value={form.baseSalary}
                onChange={(e) => setForm({ ...form, baseSalary: e.target.value })}
                hint="Max 9,999,999,999.99 (e.g. 150000)"
              />
              <div style={{ alignSelf: "end", display: "flex", gap: "var(--space-2)" }}>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={createEmp.isPending || updateEmp.isPending}
                >
                  {editingId != null ? "Save changes" : "Create Employee"}
                </Button>
                {editingId != null ? (
                  <Button type="button" variant="secondary" onClick={cancelEdit}>
                    Cancel
                  </Button>
                ) : null}
              </div>
            </form>
          </section>
        ) : null}

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
                ? "Add an employee above, or switch the filter to see terminated records."
                : "Create a department, then add your first employee record."
            }
          />
        ) : null}
        {employees.data && employees.data.items.length > 0 ? (
          <>
            <Table
              headers={
                canWrite
                  ? ["Code", "Name", "Role", "Department", "Status", "Salary", "Actions"]
                  : ["Code", "Name", "Role", "Department", "Status", "Salary"]
              }
            >
              {employees.data.items.map((e) => (
                <tr key={e.id} data-status={e.status === "active" ? "positive" : "neutral"}>
                  <td className="num">{e.employeeCode}</td>
                  <td>{e.fullName}</td>
                  <td>{e.roleTitle}</td>
                  <td>{deptNameById(e.departmentId)}</td>
                  <td>
                    <StatusBadge status={e.status === "active" ? "approved" : "draft"}>
                      {e.status}
                    </StatusBadge>
                  </td>
                  <td className="num">{e.baseSalary ?? "—"}</td>
                  {canWrite ? (
                    <td>
                      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => startEdit(e)}
                          disabled={e.status === "terminated"}
                        >
                          Edit
                        </Button>
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
