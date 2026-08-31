import { useEffect, useState } from "react";
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
import type { AdminDashboard, AttendanceTodaySnapshot } from "../../types/admin";
import type { HrModuleIconKey } from "../../constants/hrModuleIcons";
import "./DashboardPage.css";

type StatusTone = "positive" | "warning" | "critical" | "info" | "neutral";

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return reduced;
}

function AnimatedNumber({ value }: { value: number }) {
  const reduced = usePrefersReducedMotion();
  const [shown, setShown] = useState(reduced ? value : 0);

  useEffect(() => {
    if (reduced) {
      setShown(value);
      return;
    }
    const from = 0;
    const start = performance.now();
    const duration = 420;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) * (1 - t);
      setShown(Math.round(from + (value - from) * eased));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, reduced]);

  return <>{shown}</>;
}

function MetricCard({
  label,
  value,
  hint,
  to,
  status,
  icon,
}: {
  label: string;
  value: number;
  hint?: string;
  to: string;
  status: StatusTone;
  icon: HrModuleIconKey;
}) {
  const tone = value > 0 ? status : "neutral";
  return (
    <Link to={to} className="dashboard-action-link">
      <article className="dashboard-action" data-status={tone} data-active={value > 0 ? "true" : "false"}>
        <div className="dashboard-action__icon">
          <HrModuleIcon icon={icon} size="md" />
        </div>
        <div className="dashboard-action__body">
          <div className="dashboard-action__label">{label}</div>
          <div className="dashboard-action__value font-data">
            <AnimatedNumber value={value} />
          </div>
          {hint ? <p className="dashboard-action__hint">{hint}</p> : null}
        </div>
        <span className="dashboard-action__arrow" aria-hidden>
          →
        </span>
      </article>
    </Link>
  );
}

function AttendancePanel({ att }: { att: AttendanceTodaySnapshot }) {
  const segments: { key: string; count: number; kind: string; label: string; status: StatusTone; to: string }[] = [
    { key: "present", count: att.present, kind: "present", label: "Present", status: "positive", to: "/attendance" },
    { key: "late", count: att.late, kind: "late", label: "Late", status: "warning", to: "/attendance" },
    { key: "absent", count: att.absent, kind: "absent", label: "Absent", status: "critical", to: "/attendance" },
    { key: "leave", count: att.onLeave, kind: "leave", label: "On leave", status: "info", to: "/attendance/leave-requests" },
  ];
  const tracked = segments.reduce((sum, seg) => sum + seg.count, 0);

  return (
    <section className="dashboard-section" aria-label="Attendance today">
      <div className="dashboard-section__head">
        <h2 className="dashboard-section__title">Attendance today</h2>
        <Link to="/attendance" className="dashboard-section__link">
          Open attendance
        </Link>
      </div>
      <div className="dashboard-att">
        <div
          className="dashboard-att__bar"
          role="img"
          aria-label={
            tracked === 0
              ? "No attendance marked yet today"
              : `Today: ${att.present} present, ${att.late} late, ${att.absent} absent, ${att.onLeave} on leave`
          }
        >
          {tracked === 0 ? (
            <div className="dashboard-att__seg dashboard-att__seg--empty" />
          ) : (
            segments.map((seg) =>
              seg.count > 0 ? (
                <div
                  key={seg.key}
                  className="dashboard-att__seg"
                  data-kind={seg.kind}
                  style={{ flexGrow: seg.count }}
                  title={`${seg.label}: ${seg.count}`}
                />
              ) : null,
            )
          )}
        </div>
        <div className="dashboard-att__stats">
          {segments.map((seg) => (
            <Link key={seg.key} to={seg.to} className="dashboard-att__stat" data-status={seg.status}>
              <span className="dashboard-att__stat-label">{seg.label}</span>
              <span className="dashboard-att__stat-value font-data">
                <AnimatedNumber value={seg.count} />
              </span>
            </Link>
          ))}
        </div>
        {att.halfDay > 0 || att.holiday > 0 ? (
          <p className="dashboard-att__note">
            {att.halfDay > 0 ? `${att.halfDay} half day${att.halfDay === 1 ? "" : "s"}` : null}
            {att.halfDay > 0 && att.holiday > 0 ? " · " : null}
            {att.holiday > 0 ? `${att.holiday} holiday` : null}
          </p>
        ) : null}
      </div>
    </section>
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
  const today = new Date();
  const todayLabel = today.toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

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
            <section className="dashboard-hero" aria-label="Workforce overview">
              <div className="dashboard-hero__top">
                <time className="dashboard-hero__date" dateTime={today.toISOString().slice(0, 10)}>
                  {todayLabel}
                </time>
                <p className={`dashboard-hero__health dashboard-hero__health--${agentStatusRail(dash.data.agentStatus)}`}>
                  <span className="dashboard-hero__dot" aria-hidden />
                  Agent {agentStatusLabel(dash.data.agentStatus)}
                  {dash.data.agentMode === "standalone" ? " · Standalone" : " · Orchestrator"}
                </p>
              </div>
              <p className="dashboard-hero__kicker">Active employees</p>
              <Link to="/employees" className="dashboard-hero__number-link">
                <p className="dashboard-hero__number font-data">
                  <AnimatedNumber value={dash.data.hrEmployeeRecordsActive} />
                </p>
              </Link>
              <p className="dashboard-hero__meta">
                <Link to="/admin/users">{dash.data.staffUsersActive} staff logins</Link>
                <span className="dashboard-hero__sep" aria-hidden>
                  ·
                </span>
                <Link to="/employees/departments">{dash.data.departments} departments</Link>
              </p>
            </section>

            <section className="dashboard-section" aria-label="Needs attention">
              <div className="dashboard-section__head">
                <h2 className="dashboard-section__title">Needs attention</h2>
              </div>
              <div className="dashboard-actions">
                <MetricCard
                  label="Open roles"
                  value={dash.data.openJobDescriptions}
                  hint="Job postings accepting CVs"
                  to="/job-descriptions"
                  icon="recruitment"
                  status="info"
                />
                <MetricCard
                  label="CVs to review"
                  value={dash.data.candidatesPendingReview}
                  hint="Awaiting shortlist or reject"
                  to="/cv-screening"
                  icon="documentManagement"
                  status="warning"
                />
                <MetricCard
                  label="Leave to approve"
                  value={dash.data.leaveRequestsPending}
                  hint="Pending leave requests"
                  to="/attendance/leave-requests"
                  icon="leave"
                  status="warning"
                />
                <MetricCard
                  label="Payroll to approve"
                  value={dash.data.payrollRunsPendingApproval}
                  hint="Runs waiting on approval"
                  to="/payroll/runs"
                  icon="salaryReports"
                  status="warning"
                />
              </div>
            </section>

            <AttendancePanel att={dash.data.attendanceToday} />
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
