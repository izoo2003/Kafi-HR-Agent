import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useCreateLeave, useLeaveRequests, useUpdateLeave } from "../../hooks/useAttendance";
import { useEmployees } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { LEAVE_STATUS_LABELS } from "../../constants/statusLabels";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";

export function LeaveRequestsPage() {
  const { page, pageSize, setPage, params } = usePagination();
  const leaves = useLeaveRequests(params);
  const employees = useEmployees({ page: 1, pageSize: 100, status: "active" });
  const create = useCreateLeave();
  const update = useUpdateLeave();
  const { hasPermission } = useAuth();
  const canApprove = hasPermission("attendance", "approve");

  const [form, setForm] = useState({
    employeeId: "",
    leaveType: "annual" as const,
    startDate: "",
    endDate: "",
    reason: "",
  });
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await create.mutateAsync({
        employeeId: Number(form.employeeId),
        leaveType: form.leaveType,
        startDate: form.startDate,
        endDate: form.endDate,
        reason: form.reason || undefined,
      });
      setForm({ ...form, reason: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit leave request");
    }
  }

  return (
    <>
      <PageHeader
        title="Leave Requests"
        breadcrumb="Attendance / Leave Requests"
        actions={
          <Link to="/attendance">
            <Button variant="secondary">Overview</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}

        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Submit leave request</h2>
          <form
            onSubmit={onSubmit}
            style={{
              display: "grid",
              gap: "var(--space-3)",
              gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
            }}
          >
            <label className="form-field">
              <span className="form-field__label">Employee</span>
              <select
                className="form-field__input"
                value={form.employeeId}
                onChange={(e) => setForm({ ...form, employeeId: e.target.value })}
                required
              >
                <option value="">Select…</option>
                {(employees.data?.items ?? []).map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.fullName}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span className="form-field__label">Type</span>
              <select
                className="form-field__input"
                value={form.leaveType}
                onChange={(e) =>
                  setForm({ ...form, leaveType: e.target.value as typeof form.leaveType })
                }
              >
                <option value="annual">Annual</option>
                <option value="sick">Sick</option>
                <option value="unpaid">Unpaid</option>
                <option value="other">Other</option>
              </select>
            </label>
            <FormField
              label="Start"
              type="date"
              value={form.startDate}
              onChange={(e) => setForm({ ...form, startDate: e.target.value })}
              required
            />
            <FormField
              label="End"
              type="date"
              value={form.endDate}
              onChange={(e) => setForm({ ...form, endDate: e.target.value })}
              required
            />
            <FormField
              label="Reason"
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
            />
            <div style={{ alignSelf: "end" }}>
              <Button type="submit" variant="primary">
                Submit Leave Request
              </Button>
            </div>
          </form>
        </section>

        {leaves.isLoading ? <Spinner /> : null}
        {leaves.data && leaves.data.items.length === 0 ? (
          <EmptyState
            title="No leave requests"
            description="Submit a leave request. Pending leave does not change attendance until approved."
          />
        ) : null}
        {leaves.data && leaves.data.items.length > 0 ? (
          <>
            <Table headers={["Employee", "Type", "From", "To", "Status", "Actions"]}>
              {leaves.data.items.map((l) => (
                <tr key={l.id} data-status={l.status === "approved" ? "on_leave" : l.status}>
                  <td className="num">{l.employeeId}</td>
                  <td>{l.leaveType}</td>
                  <td className="num">{l.startDate}</td>
                  <td className="num">{l.endDate}</td>
                  <td>
                    <StatusBadge status={l.status === "approved" ? "on_leave" : l.status}>
                      {LEAVE_STATUS_LABELS[l.status as keyof typeof LEAVE_STATUS_LABELS] ?? l.status}
                    </StatusBadge>
                  </td>
                  <td style={{ display: "flex", gap: 8 }}>
                    {canApprove && l.status === "pending" ? (
                      <>
                        <Button
                          variant="positive"
                          onClick={() => update.mutate({ id: l.id, status: "approved" })}
                        >
                          Approve Leave
                        </Button>
                        <Button
                          variant="destructive"
                          onClick={() => update.mutate({ id: l.id, status: "rejected" })}
                        >
                          Reject Leave
                        </Button>
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={leaves.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
    </>
  );
}
