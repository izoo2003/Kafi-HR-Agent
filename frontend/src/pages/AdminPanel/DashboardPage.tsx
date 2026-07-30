import { PageHeader } from "../../components/layout/AppShell";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { StatusBadge } from "../../components/ui/Badge";
import { useAdminDashboard, useAuditLogs } from "../../hooks/useAdmin";
import { useUsers } from "../../hooks/useUsers";
import { usePagination } from "../../hooks/usePagination";
import { ApiError } from "../../api/client";

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
  const { page, pageSize, setPage, params } = usePagination();
  const users = useUsers(params);

  return (
    <>
      <PageHeader title="Users" breadcrumb="Admin / Users" />
      <div className="page">
        {users.isLoading ? <Spinner label="Loading users" /> : null}
        {users.isError ? (
          <EmptyState
            title="Could not load users"
            description={users.error instanceof ApiError ? users.error.message : "Please try again."}
          />
        ) : null}
        {users.data ? (
          <>
            <Table headers={["ID", "Name", "Email", "Active"]}>
              {users.data.items.map((u) => (
                <tr key={u.id} data-status={u.isActive ? "positive" : "neutral"}>
                  <td className="num">{u.id}</td>
                  <td>{u.fullName}</td>
                  <td>{u.email}</td>
                  <td>
                    <StatusBadge status={u.isActive ? "approved" : "draft"}>
                      {u.isActive ? "Active" : "Inactive"}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </Table>
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
