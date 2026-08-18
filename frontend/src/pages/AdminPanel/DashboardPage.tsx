import { useState, type FormEvent } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { StatusBadge } from "../../components/ui/Badge";
import { useAdminDashboard, useAuditLogs } from "../../hooks/useAdmin";
import { useSetUserPassword, useUsers } from "../../hooks/useUsers";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import { ApiError } from "../../api/client";
import type { User } from "../../types/users";

export function DashboardPage() {
  const dash = useAdminDashboard();
  return (
    <>
      <PageHeader title="Admin Dashboard" breadcrumb="Admin / Dashboard" />
      <div className="page">
        {dash.isLoading ? <Spinner /> : null}
        {dash.isError ? (
          <EmptyState
            title="Could not load dashboard"
            description={
              dash.error instanceof ApiError
                ? dash.error.message
                : "Something went wrong, please try again."
            }
          />
        ) : null}
        {dash.data ? (
          <div style={{ display: "grid", gap: "var(--space-4)", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
            <Card status="info">
              <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", textTransform: "uppercase" }}>
                Status
              </div>
              <div className="font-data" style={{ fontSize: "var(--text-2xl)", marginTop: "var(--space-2)" }}>
                {dash.data.status}
              </div>
            </Card>
            <Card>
              <p style={{ margin: 0, color: "var(--color-text-secondary)" }}>
                {dash.data.message ?? "Module scaffolds are ready. Feature packs will fill metrics."}
              </p>
            </Card>
          </div>
        ) : null}
      </div>
    </>
  );
}

export function UserManagementPage() {
  const { hasPermission } = useAuth();
  const canSetPassword = hasPermission("users", "write");
  const { page, pageSize, setPage, params } = usePagination(1, 50);
  const users = useUsers(params);
  const setPasswordMut = useSetUserPassword();
  const [resetUser, setResetUser] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [revealed, setRevealed] = useState<{
    fullName: string;
    loginIdentifier: string;
    password: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSetPassword(e: FormEvent) {
    e.preventDefault();
    if (!resetUser) return;
    setError(null);
    try {
      const res = await setPasswordMut.mutateAsync({
        userId: resetUser.id,
        password: newPassword,
      });
      setRevealed({
        fullName: res.fullName,
        loginIdentifier: res.loginIdentifier,
        password: res.password,
      });
      setResetUser(null);
      setNewPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not set password");
    }
  }

  return (
    <>
      <PageHeader title="Users" breadcrumb="Admin / Users" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Login IDs are shown below. Passwords are stored hashed and cannot be looked up — set a new
          password to share with the user (staff log in with email; self-registered employees use
          username + PIN).
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {revealed ? (
          <Card status="info">
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Share these credentials once</h2>
            <p style={{ margin: 0 }}>
              <strong>{revealed.fullName}</strong>
            </p>
            <p className="font-data" style={{ margin: "var(--space-2) 0 0" }}>
              Login: {revealed.loginIdentifier}
            </p>
            <p className="font-data" style={{ margin: "var(--space-1) 0 0" }}>
              Password / PIN: {revealed.password}
            </p>
            <div style={{ marginTop: "var(--space-3)" }}>
              <Button type="button" variant="secondary" onClick={() => setRevealed(null)}>
                Hide
              </Button>
            </div>
          </Card>
        ) : null}
        {resetUser ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>
              Set password for {resetUser.fullName}
            </h2>
            <form onSubmit={onSetPassword} style={{ display: "grid", gap: "var(--space-3)", maxWidth: 360 }}>
              <FormField
                label="New password or PIN"
                type="text"
                autoComplete="new-password"
                minLength={4}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                hint="Self-service accounts use a 4–8 digit PIN. Staff accounts can use a longer password."
              />
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                <Button type="submit" variant="primary" disabled={setPasswordMut.isPending}>
                  Save password
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
                title="No users yet"
                description="When someone creates a personal account from the register page, they will show up in this list."
              />
            ) : (
              <Table
                headers={[
                  "Name",
                  "Username",
                  "Email",
                  "Login with",
                  "Department",
                  "Roles",
                  "Active",
                  "Password",
                ]}
              >
                {users.data.items.map((u) => (
                  <tr key={u.id} data-status={u.isActive ? "positive" : "neutral"}>
                    <td>
                      {u.fullName}
                      {u.isSelfRegistered ? (
                        <div style={{ marginTop: "var(--space-1)" }}>
                          <StatusBadge status="info">Self-registered</StatusBadge>
                        </div>
                      ) : null}
                    </td>
                    <td className="font-data">{u.username ?? "—"}</td>
                    <td className="font-data">{u.email}</td>
                    <td className="font-data">{u.loginIdentifier ?? u.username ?? u.email}</td>
                    <td>{u.departmentName ?? "—"}</td>
                    <td>{u.roles.length ? u.roles.join(", ") : "—"}</td>
                    <td>
                      <StatusBadge status={u.isActive ? "approved" : "draft"}>
                        {u.isActive ? "Active" : "Inactive"}
                      </StatusBadge>
                    </td>
                    <td>
                      {canSetPassword ? (
                        <Button type="button" variant="secondary" onClick={() => setResetUser(u)}>
                          Set password
                        </Button>
                      ) : (
                        <span style={{ color: "var(--color-text-muted)" }}>Hashed — not viewable</span>
                      )}
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

export function AuditLogPage() {
  const { page, pageSize, setPage, params } = usePagination();
  const logs = useAuditLogs(params);

  return (
    <>
      <PageHeader title="Audit Log" breadcrumb="Admin / Audit Log" />
      <div className="page">
        {logs.isLoading ? <Spinner label="Loading audit log" /> : null}
        {logs.data && logs.data.items.length === 0 ? (
          <EmptyState
            title="No audit entries yet"
            description="Login and write actions will appear here automatically."
          />
        ) : null}
        {logs.data && logs.data.items.length > 0 ? (
          <>
            <Table headers={["When", "Action", "Entity", "User"]}>
              {logs.data.items.map((row) => (
                <tr key={row.id} data-status="info">
                  <td className="num">{new Date(row.timestamp).toLocaleString()}</td>
                  <td>{row.action}</td>
                  <td className="font-data">
                    {row.entityType ?? "—"}
                    {row.entityId != null ? ` #${row.entityId}` : ""}
                  </td>
                  <td className="num">{row.userId ?? "—"}</td>
                </tr>
              ))}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={logs.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
    </>
  );
}

export function SystemConfigPage() {
  return (
    <>
      <PageHeader title="System Config" breadcrumb="Admin / Config" />
      <div className="page">
        <EmptyState
          title="Runtime config"
          description="Key/value system_config editor will land with FEATURE_ADMIN_PANEL.md."
        />
      </div>
    </>
  );
}
