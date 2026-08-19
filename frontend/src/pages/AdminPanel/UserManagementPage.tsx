import { useState, type CSSProperties, type FormEvent } from "react";
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
import { useDepartments } from "../../hooks/useEmployees";
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

const selectStyle: CSSProperties = {
  minWidth: 180,
  padding: "var(--space-2) var(--space-3)",
  border: "1px solid var(--color-border-strong)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-surface)",
  fontFamily: "var(--font-ui)",
  fontSize: "var(--text-sm)",
  color: "var(--color-text-primary)",
};

function UsersSectionMenu({ current }: { current: "list" | "create" }) {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("users", "write");

  return (
    <label className="form-field" style={{ margin: 0 }}>
      <span className="form-field__label">Create User</span>
      <select
        className="form-field__input"
        style={selectStyle}
        value={current}
        aria-label="Create User"
        onChange={(e) => {
          const value = e.target.value;
          if (value === "create") navigate("/admin/users/new");
          else navigate("/admin/users");
        }}
      >
        <option value="list">View users</option>
        {canWrite ? <option value="create">Create User</option> : null}
      </select>
    </label>
  );
}

export function UserManagementPage() {
  const { hasPermission, user } = useAuth();
  const canWrite = hasPermission("users", "write");
  const { page, pageSize, setPage, params } = usePagination(1, 50);
  const users = useUsers(params);
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
        title="Users"
        breadcrumb="Admin / Users"
        actions={<UsersSectionMenu current="list" />}
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Stored PINs are listed below. If a row says “Not stored”, use Change PIN, or the PIN
          appears after that person signs in once. Use the Create User option in the dropdown to add
          a login.
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
                title="No logins yet"
                description="Open the Users dropdown and choose Create User to add a username, PIN, and department."
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
  const departments = useDepartments(canWrite);
  const createUser = useCreateUser();
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!canWrite) return;
    setError(null);
    try {
      await createUser.mutateAsync({
        fullName: fullName.trim(),
        username: username.trim().toLowerCase(),
        pin,
        departmentId: Number(departmentId),
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
          title="Create User"
          breadcrumb="Admin / Users / Create User"
          actions={<UsersSectionMenu current="create" />}
        />
        <div className="page">
          <EmptyState
            title="Not allowed"
            description="You need write access on Users to create logins."
          />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Create User"
        breadcrumb="Admin / Users / Create User"
        actions={<UsersSectionMenu current="create" />}
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Set a full name, username, 4–8 digit PIN, and department. That person can then sign in. The
          PIN stays visible on the users list.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        <Card>
          <form
            onSubmit={onCreate}
            style={{ display: "grid", gap: "var(--space-3)", maxWidth: 420 }}
          >
            <FormField
              label="Full name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
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
              hint="4–8 digits. Shown in the users list after save."
            />
            <label style={{ display: "grid", gap: "var(--space-1)" }}>
              <span
                style={{
                  fontSize: "var(--text-sm)",
                  fontWeight: "var(--weight-medium)",
                  color: "var(--color-text-secondary)",
                }}
              >
                Department
              </span>
              <select
                required
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
                style={selectStyle}
              >
                <option value="">Select department</option>
                {(departments.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <Button type="submit" variant="primary" disabled={createUser.isPending}>
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
