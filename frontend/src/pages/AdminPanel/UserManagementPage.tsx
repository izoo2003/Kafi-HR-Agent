import { useState, useMemo, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { ApiError } from "../../api/client";
import { useCreateUser, useDeactivateUser, useSetUserPassword, useUsers } from "../../hooks/useUsers";
import { useEmployees } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import type { User } from "../../types/users";

const STAFF_ROLES = new Set([
  "super_admin",
  "hr_manager",
  "payroll_officer",
  "department_head",
  "recruiter",
  "readonly_auditor",
]);

export function UserManagementPage() {
  const { hasPermission, user } = useAuth();
  const canWrite = hasPermission("users", "write");
  const { page, pageSize, setPage, params } = usePagination(1, 50);
  const users = useUsers({ ...params, selfRegisteredOnly: true });
  const setPasswordMut = useSetUserPassword();
  const deactivateUser = useDeactivateUser();
  const [resetUser, setResetUser] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSetPassword(e: FormEvent) {
    e.preventDefault();
    if (!resetUser) return;
    setError(null);
    try {
      await setPasswordMut.mutateAsync({
        userId: resetUser.id,
        password: newPassword,
      });
      setResetUser(null);
      setNewPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not set PIN");
    }
  }

  async function onRemoveUser(u: User) {
    const ok = window.confirm(
      `Remove login for ${u.fullName} (${u.username ?? u.loginIdentifier})?\n\nThey will not be able to sign in. Their linked employee record is marked terminated.`,
    );
    if (!ok) return;
    setError(null);
    try {
      await deactivateUser.mutateAsync(u.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove user");
    }
  }

  return (
    <>
      <PageHeader
        title="View Users"
        breadcrumb="Admin / User Management / View Users"
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Registered user accounts only (username + PIN). Staff management logins are not listed
          here. Stored PINs appear below; if a row says “Not stored”, use Change PIN.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}

        {resetUser ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>
              Change PIN for {resetUser.fullName}
            </h2>
            <form onSubmit={onSetPassword} style={{ display: "grid", gap: "var(--space-3)", maxWidth: 360 }}>
              <FormField
                label="New PIN"
                type="text"
                inputMode="numeric"
                autoComplete="off"
                minLength={4}
                maxLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                hint="4–8 digits. It will stay visible in this list."
              />
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                <Button type="submit" variant="primary" disabled={setPasswordMut.isPending}>
                  Save PIN
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setResetUser(null);
                    setNewPassword("");
                  }}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        {users.isLoading ? <Spinner label="Loading users" /> : null}
        {users.isError ? (
          <EmptyState
            title="Could not load users"
            description={users.error instanceof ApiError ? users.error.message : "Please try again."}
          />
        ) : null}
        {users.data ? (
          <>
            {users.data.items.length === 0 ? (
              <EmptyState
                title="No user accounts yet"
                description="Use Create Users in the sidebar to pick an employee and assign a username and PIN."
              />
            ) : (
              <Table headers={["Name", "Username", "PIN / password", "Department", "Active", ""]}>
                {users.data.items.map((u) => (
                  <tr key={u.id} data-status={u.isActive ? "positive" : "neutral"}>
                    <td>{u.fullName}</td>
                    <td className="font-data">{u.username ?? u.loginIdentifier ?? "—"}</td>
                    <td className="font-data">{u.loginPin?.trim() ? u.loginPin : "Not stored"}</td>
                    <td>{u.departmentName ?? "—"}</td>
                    <td>
                      <StatusBadge status={u.isActive ? "approved" : "draft"}>
                        {u.isActive ? "Active" : "Inactive"}
                      </StatusBadge>
                    </td>
                    <td>
                      {canWrite ? (
                        <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                          <Button type="button" variant="secondary" onClick={() => setResetUser(u)}>
                            Change PIN
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            disabled={
                              !u.isActive ||
                              deactivateUser.isPending ||
                              u.id === user?.userId ||
                              (u.roles ?? []).some((r) => STAFF_ROLES.has(r))
                            }
                            onClick={() => onRemoveUser(u)}
                          >
                            Remove
                          </Button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </Table>
            )}
            <Pagination
              page={page}
              pageSize={pageSize}
              total={users.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
    </>
  );
}

export function CreateUserPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("users", "write");
  const employees = useEmployees({ page: 1, pageSize: 500, status: "active", enabled: canWrite });
  const createUser = useCreateUser();
  const [employeeId, setEmployeeId] = useState("");
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);

  const employeesWithoutLogin = useMemo(
    () => (employees.data?.items ?? []).filter((e) => e.userId == null),
    [employees.data?.items],
  );

  const selectedEmployee = employeesWithoutLogin.find((e) => String(e.id) === employeeId);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!canWrite) return;
    setError(null);
    try {
      await createUser.mutateAsync({
        employeeId: Number(employeeId),
        username: username.trim().toLowerCase(),
        pin,
      });
      navigate("/admin/users", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create user");
    }
  }

  if (!canWrite) {
    return (
      <>
        <PageHeader
          title="Create Users"
          breadcrumb="Admin / User Management / Create Users"
        />
        <div className="page">
          <EmptyState
            title="Not allowed"
            description="You need write access on User Management to create logins."
          />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Create Users"
        breadcrumb="Admin / User Management / Create Users"
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Choose an employee who does not have a login yet, then set their username and 4–8 digit PIN.
          Department comes from the employee record automatically.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {employees.isLoading ? <Spinner label="Loading employees" /> : null}
        {employeesWithoutLogin.length === 0 && !employees.isLoading ? (
          <EmptyState
            title="No employees without logins"
            description="Every active employee already has an account, or you need to add employees first under Employees."
          />
        ) : null}
        <Card>
          <form
            onSubmit={onCreate}
            style={{ display: "grid", gap: "var(--space-3)", maxWidth: 420 }}
          >
            <label style={{ display: "grid", gap: "var(--space-1)" }}>
              <span
                style={{
                  fontSize: "var(--text-sm)",
                  fontWeight: "var(--weight-medium)",
                  color: "var(--color-text-secondary)",
                }}
              >
                Employee
              </span>
              <select
                required
                className="form-field__input"
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                disabled={employeesWithoutLogin.length === 0}
              >
                <option value="">Select employee</option>
                {employeesWithoutLogin.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.fullName} ({emp.employeeCode}) — {emp.roleTitle}
                  </option>
                ))}
              </select>
            </label>
            {selectedEmployee ? (
              <p
                style={{
                  margin: 0,
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-muted)",
                }}
              >
                Login will be linked to{" "}
                <strong>{selectedEmployee.fullName}</strong> in {selectedEmployee.roleTitle}.
              </p>
            ) : null}
            <FormField
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              hint="Letters, numbers, dots, underscores, hyphens."
            />
            <FormField
              label="PIN"
              type="text"
              inputMode="numeric"
              autoComplete="off"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              required
              minLength={4}
              maxLength={8}
              hint="4–8 digits. Shown under View Users after save."
            />
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <Button
                type="submit"
                variant="primary"
                disabled={createUser.isPending || employeesWithoutLogin.length === 0}
              >
                {createUser.isPending ? "Creating…" : "Create account"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate("/admin/users")}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </>
  );
}
