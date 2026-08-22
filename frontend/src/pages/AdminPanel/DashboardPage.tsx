import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { HrModuleIcon } from "../../components/ui/HrModuleIcon";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useAdminDashboard, useAuditLogs } from "../../hooks/useAdmin";
import { usePagination } from "../../hooks/usePagination";
import { ApiError } from "../../api/client";
import type { AdminDashboard } from "../../types/admin";
import type { HrModuleIconKey } from "../../constants/hrModuleIcons";
import "./DashboardPage.css";

function MetricCard({
  label,
  value,
  hint,
  to,
  status,
  icon,
  accent,
}: {
  label: string;
  value: number | string;
  hint?: string;
  to?: string;
  status?: string;
  icon: HrModuleIconKey;
  accent?: "blue" | "green" | "amber" | "rose" | "violet" | "slate";
}) {
  const body = (
    <article
      className={`dashboard-metric dashboard-metric--${accent ?? "slate"}`}
      data-status={status}
    >
      <div className="dashboard-metric__icon-wrap">
        <HrModuleIcon icon={icon} size="lg" />
      </div>
      <div className="dashboard-metric__body">
        <div className="dashboard-metric__label">{label}</div>
        <div className="dashboard-metric__value font-data">{value}</div>
        {hint ? <p className="dashboard-metric__hint">{hint}</p> : null}
      </div>
      {to ? <span className="dashboard-metric__arrow" aria-hidden>→</span> : null}
    </article>
  );

  if (!to) return body;

  return (
    <Link to={to} className="dashboard-metric-link">
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

const QUICK_LINKS: { to: string; label: string; icon: HrModuleIconKey }[] = [
  { to: "/employees", label: "Employees", icon: "employeeDirectory" },
  { to: "/cv-screening", label: "CV Screening", icon: "recruitment" },
  { to: "/attendance", label: "Attendance", icon: "attendance" },
  { to: "/payroll/runs", label: "Payroll", icon: "payroll" },
  { to: "/employee-development/performance", label: "Development", icon: "trainingDevelopment" },
  { to: "/hr-policies", label: "HR Policies", icon: "compliancePolicies" },
];

export function DashboardPage() {
  const dash = useAdminDashboard();

  return (
    <>
      <PageHeader title="Admin Dashboard" breadcrumb="Admin / Dashboard" />
      <div className="page dashboard-page">
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
            <section className="dashboard-hero" aria-label="Overview">
              <div className="dashboard-hero__glow dashboard-hero__glow--a" aria-hidden />
              <div className="dashboard-hero__glow dashboard-hero__glow--b" aria-hidden />
              <div className="dashboard-hero__content">
                <div className="dashboard-hero__badge">
                  <HrModuleIcon icon="hrAiAssistant" size="sm" label="" />
                  <span>HR Admin Agent</span>
                </div>
                <h2 className="dashboard-hero__title">Operations at a glance</h2>
                <p className="dashboard-hero__subtitle">
                  {dash.data.registeredEmployeesActive} active accounts ·{" "}
                  {dash.data.hrEmployeeRecordsActive} HR records ·{" "}
                  {dash.data.departments} departments
                </p>
                <div className="dashboard-hero__status" data-status={agentStatusRail(dash.data.agentStatus)}>
                  <HrModuleIcon icon="analyticsDashboard" size="sm" />
                  <span>
                    Agent {agentStatusLabel(dash.data.agentStatus)}
                    {dash.data.agentMode === "standalone" ? " · Standalone" : " · Orchestrator"}
                  </span>
                </div>
              </div>
              <div className="dashboard-hero__visual" aria-hidden>
                <HrModuleIcon icon="analyticsDashboard" size="xl" className="dashboard-hero__featured-icon" />
              </div>
            </section>

            <section className="dashboard-quick-links" aria-label="Quick navigation">
              {QUICK_LINKS.map((item) => (
                <Link key={item.to} to={item.to} className="dashboard-quick-link">
                  <HrModuleIcon icon={item.icon} size="md" />
                  <span>{item.label}</span>
                </Link>
              ))}
            </section>

            <section className="dashboard-section">
              <h2 className="dashboard-section__title">Organization</h2>
              <div className="dashboard-grid">
                <MetricCard
                  label="User accounts"
                  value={dash.data.registeredEmployeesActive}
                  hint="Registered logins"
                  to="/admin/users"
                  icon="addEmployee"
                  accent="violet"
                  status="positive"
                />
                <MetricCard
                  label="HR employee records"
                  value={dash.data.hrEmployeeRecordsActive}
                  hint="Employees module roster"
                  to="/employees"
                  icon="employeeDirectory"
                  accent="blue"
                />
                <MetricCard
                  label="Departments"
                  value={dash.data.departments}
                  to="/employees/departments"
                  icon="employeeDirectory"
                  accent="slate"
                />
                <MetricCard
                  label="Agent status"
                  value={agentStatusLabel(dash.data.agentStatus)}
                  hint={dash.data.agentMode === "standalone" ? "Standalone mode" : "Orchestrator linked"}
                  icon="hrAiAssistant"
                  accent="green"
                  status={agentStatusRail(dash.data.agentStatus)}
                />
              </div>
            </section>

            <section className="dashboard-section">
              <h2 className="dashboard-section__title">Needs attention</h2>
              <div className="dashboard-grid">
                <MetricCard
                  label="Open job postings"
                  value={dash.data.openJobDescriptions}
                  to="/job-descriptions"
                  icon="recruitment"
                  accent="green"
                  status={dash.data.openJobDescriptions > 0 ? "info" : undefined}
                />
                <MetricCard
                  label="CVs pending review"
                  value={dash.data.candidatesPendingReview}
                  to="/cv-screening"
                  icon="documentManagement"
                  accent="amber"
                  status={dash.data.candidatesPendingReview > 0 ? "warning" : undefined}
                />
                <MetricCard
                  label="Leave requests"
                  value={dash.data.leaveRequestsPending}
                  hint="Awaiting approval"
                  to="/attendance/leave-requests"
                  icon="leave"
                  accent="rose"
                  status={dash.data.leaveRequestsPending > 0 ? "warning" : undefined}
                />
                <MetricCard
                  label="Payroll awaiting approval"
                  value={dash.data.payrollRunsPendingApproval}
                  to="/payroll/runs"
                  icon="salaryReports"
                  accent="violet"
                  status={dash.data.payrollRunsPendingApproval > 0 ? "warning" : undefined}
                />
              </div>
            </section>

            <section className="dashboard-section">
              <h2 className="dashboard-section__title">Attendance today</h2>
              <div className="dashboard-grid dashboard-grid--compact">
                <MetricCard
                  label="Present"
                  value={dash.data.attendanceToday.present}
                  to="/attendance"
                  icon="attendance"
                  accent="green"
                  status="positive"
                />
                <MetricCard
                  label="Late"
                  value={dash.data.attendanceToday.late}
                  to="/attendance"
                  icon="timeShift"
                  accent="amber"
                  status="warning"
                />
                <MetricCard
                  label="Absent"
                  value={dash.data.attendanceToday.absent}
                  to="/attendance"
                  icon="attendance"
                  accent="rose"
                  status="critical"
                />
                <MetricCard
                  label="On leave"
                  value={dash.data.attendanceToday.onLeave}
                  to="/attendance/leave-requests"
                  icon="leave"
                  accent="blue"
                  status="info"
                />
                <MetricCard
                  label="Half day"
                  value={dash.data.attendanceToday.halfDay}
                  to="/attendance"
                  icon="timeShift"
                  accent="slate"
                />
                <MetricCard
                  label="Marked today"
                  value={dash.data.attendanceToday.totalMarked}
                  hint="Records logged"
                  to="/attendance/records"
                  icon="attendance"
                  accent="slate"
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
