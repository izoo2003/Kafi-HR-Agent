import { useState, type CSSProperties, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
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
import type { Department } from "../../types/employees";

function emptyToNull(v: string): string | null {
  const t = v.trim();
  return t ? t : null;
}

function previewText(value: string | null | undefined, max = 160): string {
  const t = (value ?? "").trim();
  if (!t) return "—";
  if (t.length <= max) return t;
  return `${t.slice(0, max).trimEnd()}…`;
}

function textCellStyle(): CSSProperties {
  return {
    maxWidth: 280,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    verticalAlign: "top",
  };
}

export function DepartmentManagePage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const departments = useDepartments();
  const createDept = useCreateDepartment();
  const updateDept = useUpdateDepartment();
  const deleteDept = useDeleteDepartment();

  const [deptName, setDeptName] = useState("");
  const [deptJd, setDeptJd] = useState("");
  const [deptSops, setDeptSops] = useState("");

  const [editingDeptId, setEditingDeptId] = useState<number | null>(null);
  const [editingDeptName, setEditingDeptName] = useState("");
  const [editingDeptJd, setEditingDeptJd] = useState("");
  const [editingDeptSops, setEditingDeptSops] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function clearEdit() {
    setEditingDeptId(null);
    setEditingDeptName("");
    setEditingDeptJd("");
    setEditingDeptSops("");
  }

  function startEdit(d: Department) {
    setEditingDeptId(d.id);
    setEditingDeptName(d.name);
    setEditingDeptJd(d.jobDescriptionText ?? "");
    setEditingDeptSops(d.sopsText ?? "");
    setError(null);
    setMessage(null);
  }

  async function onCreateDept(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createDept.mutateAsync({
        name: deptName.trim(),
        jobDescriptionText: emptyToNull(deptJd),
        sopsText: emptyToNull(deptSops),
      });
      setDeptName("");
      setDeptJd("");
      setDeptSops("");
      setMessage("Department created — it will appear when creating or editing an employee.");
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
      await updateDept.mutateAsync({
        id,
        payload: {
          name,
          jobDescriptionText: emptyToNull(editingDeptJd),
          sopsText: emptyToNull(editingDeptSops),
        },
      });
      clearEdit();
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
      if (editingDeptId === id) clearEdit();
      setMessage(`Department "${name}" removed.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove department");
    }
  }

  const tableHeaders = canWrite
    ? ["Department", "Job Description", "SOPs", "Actions"]
    : ["Department", "Job Description", "SOPs"];

  return (
    <>
      <PageHeader title="Departments" breadcrumb="Organization / Employees Management / Departments" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Create departments with their job description and SOPs. These are the roles you assign on
          employee records.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        {canWrite ? (
          <Card>
            <form onSubmit={onCreateDept} style={{ display: "grid", gap: "var(--space-4)" }}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Create Department</h2>
              <FormField
                label="Department name"
                value={deptName}
                onChange={(e) => setDeptName(e.target.value)}
                required
              />
              <label className="form-field">
                <span className="form-field__label">Job Description</span>
                <textarea
                  className="form-field__input"
                  rows={5}
                  value={deptJd}
                  onChange={(e) => setDeptJd(e.target.value)}
                  placeholder="Duties and responsibilities for this department role…"
                />
              </label>
              <label className="form-field">
                <span className="form-field__label">SOPs</span>
                <textarea
                  className="form-field__input"
                  rows={5}
                  value={deptSops}
                  onChange={(e) => setDeptSops(e.target.value)}
                  placeholder="Standard operating procedures for this department…"
                />
              </label>
              <div>
                <Button type="submit" variant="primary" disabled={createDept.isPending}>
                  {createDept.isPending ? "Creating…" : "Create Department"}
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        {departments.isLoading ? <Spinner label="Loading departments" /> : null}
        {(departments.data ?? []).length === 0 && !departments.isLoading ? (
          <EmptyState
            title="No departments yet"
            description="Create a department above with its job description and SOPs. Employees pick one as their role."
          />
        ) : (
          <Table headers={tableHeaders}>
            {(departments.data ?? []).map((d) => {
              const isEditing = editingDeptId === d.id;
              return (
                <tr key={d.id}>
                  <td style={{ verticalAlign: "top", minWidth: 160 }}>
                    {isEditing ? (
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
                  <td style={textCellStyle()}>
                    {isEditing ? (
                      <textarea
                        className="form-field__input"
                        rows={4}
                        value={editingDeptJd}
                        onChange={(e) => setEditingDeptJd(e.target.value)}
                        aria-label={`Job description for ${d.name}`}
                      />
                    ) : (
                      previewText(d.jobDescriptionText)
                    )}
                  </td>
                  <td style={textCellStyle()}>
                    {isEditing ? (
                      <textarea
                        className="form-field__input"
                        rows={4}
                        value={editingDeptSops}
                        onChange={(e) => setEditingDeptSops(e.target.value)}
                        aria-label={`SOPs for ${d.name}`}
                      />
                    ) : (
                      previewText(d.sopsText)
                    )}
                  </td>
                  {canWrite ? (
                    <td className="col-actions" style={{ verticalAlign: "top" }}>
                      <div
                        className="table-actions"
                        style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}
                      >
                        {isEditing ? (
                          <>
                            <Button
                              type="button"
                              variant="primary"
                              disabled={updateDept.isPending}
                              onClick={() => onSaveDept(d.id)}
                            >
                              Save
                            </Button>
                            <Button type="button" variant="secondary" onClick={clearEdit}>
                              Cancel
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button type="button" variant="secondary" onClick={() => startEdit(d)}>
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
              );
            })}
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
