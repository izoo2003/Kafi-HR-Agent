import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { useAdminDashboard } from "../../hooks/useAdmin";
import { ApiError } from "../../api/client";
import type { AdminDashboard } from "../../types/admin";

function MetricCard({
  label,
  value,
  hint,
  to,
  status,
}: {
  label: string;
  value: number | string;
  hint?: string;
  to?: string;
  status?: string;
}) {
  const body = (
    <Card status={status}>
      <div
        style={{
          fontSize: "var(--text-xs)",
          color: "var(--color-text-secondary)",
          textTransform: "uppercase",
          letterSpacing: "0.02em",
          fontWeight: "var(--weight-semibold)",
        }}
      >
        {label}
      </div>
      <div className="font-data" style={{ fontSize: "var(--text-2xl)", marginTop: "var(--space-2)" }}>
        {value}
      </div>
      {hint ? (
        <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          {hint}
        </p>
      ) : null}
    </Card>
  );

  if (!to) return body;

  return (
    <Link
      to={to}
      style={{ textDecoration: "none", color: "inherit", display: "block" }}
      className="dashboard-metric-link"
    >
      {body}
    </Link>
  );
}

function agentStatusLabel(status: AdminDashboard["agentStatus"]): string {
  if (status === "ok") return "Healthy";
  if (status === "degraded") return "Degraded";
  return "Down";
}

function agentStatusRail(status: AdminDashboard["agentStatus"]): string {
  if (status === "ok") return "positive";
  if (status === "degraded") return "warning";
  return "critical";
}

export function DashboardPage() {
  const dash = useAdminDashboard();

  return (
    <>
      <PageHeader title="Admin Dashboard" breadcrumb="Admin / Dashboard" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {dash.isLoading ? <Spinner label="Loading dashboard" /> : null}
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
          <>
            <section
              style={{
                display: "grid",
                gap: "var(--space-4)",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              }}
            >
              <MetricCard
                label="Registered employees"
                value={dash.data.registeredEmployeesActive}
                hint="Self-service signups only (username + PIN)"
                to="/admin/users"
                status="positive"
              />
              <MetricCard
                label="Staff accounts"
                value={dash.data.staffUsersActive}
                hint="HR admin, auditor, payroll, recruiter, etc."
                to="/admin/users"
                status="info"
              />
              <MetricCard
                label="HR employee records"
                value={dash.data.hrEmployeeRecordsActive}
                hint="Roster maintained in Employees module"
                to="/employees"
              />
              <MetricCard
                label="Departments"
                value={dash.data.departments}
                to="/employees"
              />
              <MetricCard
                label="Agent status"
                value={agentStatusLabel(dash.data.agentStatus)}
                hint={dash.data.agentMode === "standalone" ? "Standalone mode" : "Registered with orchestrator"}
                status={agentStatusRail(dash.data.agentStatus)}
              />
            </section>

            <section>
              <h2 style={{ margin: "0 0 var(--space-3)", fontSize: "var(--text-lg)" }}>Needs attention</h2>
              <div
                style={{
                  display: "grid",
                  gap: "var(--space-4)",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                }}
              >
                <MetricCard
                  label="Open job postings"
                  value={dash.data.openJobDescriptions}
                  to="/job-descriptions"
                  status={dash.data.openJobDescriptions > 0 ? "info" : undefined}
                />
                <MetricCard
                  label="CVs pending review"
                  value={dash.data.candidatesPendingReview}
                  to="/cv-screening"
                  status={dash.data.candidatesPendingReview > 0 ? "warning" : undefined}
                />
                <MetricCard
                  label="Leave requests"
                  value={dash.data.leaveRequestsPending}
                  hint="Awaiting approval"
                  to="/attendance/leave-requests"
                  status={dash.data.leaveRequestsPending > 0 ? "warning" : undefined}
                />
                <MetricCard
                  label="Payroll awaiting approval"
                  value={dash.data.payrollRunsPendingApproval}
                  to="/payroll/runs"
                  status={dash.data.payrollRunsPendingApproval > 0 ? "warning" : undefined}
                />
              </div>
            </section>

            <section>
              <h2 style={{ margin: "0 0 var(--space-3)", fontSize: "var(--text-lg)" }}>
                Attendance today
              </h2>
              <div
                style={{
                  display: "grid",
                  gap: "var(--space-4)",
                  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                }}
              >
                <MetricCard
                  label="Present"
                  value={dash.data.attendanceToday.present}
                  to="/attendance"
                  status="positive"
                />
                <MetricCard
                  label="Late"
                  value={dash.data.attendanceToday.late}
                  to="/attendance"
                  status="warning"
                />
                <MetricCard
                  label="Absent"
                  value={dash.data.attendanceToday.absent}
                  to="/attendance"
                  status="critical"
                />
                <MetricCard
                  label="On leave"
                  value={dash.data.attendanceToday.onLeave}
                  to="/attendance/leave-requests"
                  status="info"
                />
                <MetricCard
                  label="Half day"
                  value={dash.data.attendanceToday.halfDay}
                  to="/attendance"
                />
                <MetricCard
                  label="Marked today"
                  value={dash.data.attendanceToday.totalMarked}
                  hint="Records logged for today"
                  to="/attendance/records"
                />
              </div>
            </section>
          </>
        ) : null}
      </div>
    </>
  );
}

import { useState, type FormEvent } from "react";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useAuditLogs } from "../../hooks/useAdmin";
import { useCreateUser, useSetUserPassword, useUsers } from "../../hooks/useUsers";
import { useDepartments } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import type { User } from "../../types/users";

export function UserManagementPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("users", "write");
  const { page, pageSize, setPage, params } = usePagination(1, 50);
  const users = useUsers(params);
  const departments = useDepartments(canWrite);
  const createUser = useCreateUser();
  const setPasswordMut = useSetUserPassword();
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [resetUser, setResetUser] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
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
      setFullName("");
      setUsername("");
      setPin("");
      setDepartmentId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create user");
    }
  }

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

  return (
    <>
      <PageHeader title="Users" breadcrumb="Admin / Users" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Only an administrator can create login accounts. Set a username, 4–8 digit PIN, and
          department. That person can then sign in. Usernames and PINs stay visible here because you
          issued them.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}

        {canWrite ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Create user</h2>
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
                hint="4–8 digits. Shown in the table after save."
              />
              <label style={{ display: "grid", gap: "var(--space-1)" }}>
                <span style={{ fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)", color: "var(--color-text-secondary)" }}>
                  Department
                </span>
                <select
                  required
                  value={departmentId}
                  onChange={(e) => setDepartmentId(e.target.value)}
                  style={{
                    padding: "var(--space-2) var(--space-3)",
                    border: "1px solid var(--color-border-strong)",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--color-surface)",
                  }}
                >
                  <option value="">Select department</option>
                  {(departments.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <Button type="submit" variant="primary" disabled={createUser.isPending}>
                {createUser.isPending ? "Creating…" : "Create account"}
              </Button>
            </form>
          </Card>
        ) : null}

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
                title="No employee logins yet"
                description="Create a username, PIN, and department above. Staff admin accounts are not listed here."
              />
            ) : (
              <Table headers={["Name", "Username", "PIN", "Department", "Active", ""]}>
                {users.data.items.map((u) => (
                  <tr key={u.id} data-status={u.isActive ? "positive" : "neutral"}>
                    <td>{u.fullName}</td>
                    <td className="font-data">{u.username ?? u.loginIdentifier ?? "—"}</td>
                    <td className="font-data">{u.loginPin ?? "—"}</td>
                    <td>{u.departmentName ?? "—"}</td>
                    <td>
                      <StatusBadge status={u.isActive ? "approved" : "draft"}>
                        {u.isActive ? "Active" : "Inactive"}
                      </StatusBadge>
                    </td>
                    <td>
                      {canWrite ? (
                        <Button type="button" variant="secondary" onClick={() => setResetUser(u)}>
                          Change PIN
                        </Button>
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
