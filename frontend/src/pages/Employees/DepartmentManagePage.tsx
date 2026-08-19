import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { ApiError } from "../../api/client";
import {
  useCreateDepartment,
  useDeleteDepartment,
  useDepartments,
  useUpdateDepartment,
} from "../../hooks/useEmployees";
import { useAuth } from "../../hooks/useAuth";

export function DepartmentManagePage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const departments = useDepartments();
  const createDept = useCreateDepartment();
  const updateDept = useUpdateDepartment();
  const deleteDept = useDeleteDepartment();

  const [deptName, setDeptName] = useState("");
  const [editingDeptId, setEditingDeptId] = useState<number | null>(null);
  const [editingDeptName, setEditingDeptName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function onCreateDept(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createDept.mutateAsync({ name: deptName.trim() });
      setDeptName("");
      setMessage("Department added — it will appear when creating or editing an employee.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create department");
    }
  }

  async function onSaveDept(id: number) {
    const name = editingDeptName.trim();
    if (!name) {
      setError("Department name cannot be empty.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      await updateDept.mutateAsync({ id, payload: { name } });
      setEditingDeptId(null);
      setEditingDeptName("");
      setMessage("Department updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update department");
    }
  }

  async function onDeleteDept(id: number, name: string) {
    const ok = window.confirm(
      `Remove department "${name}"?\n\nThis is only allowed if no employees, job descriptions, KPI definitions, or attendance rules still use it.`,
    );
    if (!ok) return;
    setError(null);
    setMessage(null);
    try {
      await deleteDept.mutateAsync(id);
      if (editingDeptId === id) {
        setEditingDeptId(null);
        setEditingDeptName("");
      }
      setMessage(`Department "${name}" removed.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove department");
    }
  }

  return (
    <>
      <PageHeader title="Departments" breadcrumb="Organization / Employees / Departments" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Create, rename, or remove departments. These are the roles you assign on employee records.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        {canWrite ? (
          <form
            onSubmit={onCreateDept}
            style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap", alignItems: "end" }}
          >
            <FormField
              label="New department"
              value={deptName}
              onChange={(e) => setDeptName(e.target.value)}
              required
            />
            <div>
              <Button type="submit" variant="primary" disabled={createDept.isPending}>
                {createDept.isPending ? "Adding…" : "Add department"}
              </Button>
            </div>
          </form>
        ) : null}

        {departments.isLoading ? <Spinner label="Loading departments" /> : null}
        {(departments.data ?? []).length === 0 && !departments.isLoading ? (
          <EmptyState
            title="No departments yet"
            description="Add a department name above. Employees pick one as their role."
          />
        ) : (
          <Table headers={canWrite ? ["Department", "Actions"] : ["Department"]}>
            {(departments.data ?? []).map((d) => (
              <tr key={d.id}>
                <td>
                  {editingDeptId === d.id ? (
                    <input
                      className="form-field__input"
                      value={editingDeptName}
                      onChange={(e) => setEditingDeptName(e.target.value)}
                      aria-label={`Rename ${d.name}`}
                    />
                  ) : (
                    d.name
                  )}
                </td>
                {canWrite ? (
                  <td className="col-actions">
                    <div className="table-actions" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
                      {editingDeptId === d.id ? (
                        <>
                          <Button
                            type="button"
                            variant="primary"
                            disabled={updateDept.isPending}
                            onClick={() => onSaveDept(d.id)}
                          >
                            Save
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => {
                              setEditingDeptId(null);
                              setEditingDeptName("");
                            }}
                          >
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => {
                              setEditingDeptId(d.id);
                              setEditingDeptName(d.name);
                            }}
                          >
                            Edit
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            disabled={deleteDept.isPending}
                            onClick={() => onDeleteDept(d.id, d.name)}
                          >
                            Remove
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                ) : null}
              </tr>
            ))}
          </Table>
        )}

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
