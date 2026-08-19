import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useAdminDashboard, useAuditLogs } from "../../hooks/useAdmin";
import { usePagination } from "../../hooks/usePagination";
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
                gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))",
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
                  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))",
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
