import { useEffect, useState, type FormEvent } from "react";
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
import { isSelfService } from "../../lib/selfService";

export function LeaveRequestsPage() {
  const { hasPermission, user } = useAuth();
  const selfService = isSelfService(user);
  const canApprove = hasPermission("attendance", "approve");
  const canWrite = hasPermission("attendance", "write");
  const canSubmit = selfService || canWrite;
  const { page, pageSize, setPage, params } = usePagination();
  const leaves = useLeaveRequests(params);
  const employees = useEmployees({
    page: 1,
    pageSize: 100,
    status: "active",
    enabled: canWrite && !selfService,
  });
  const create = useCreateLeave();
  const update = useUpdateLeave();

  const [form, setForm] = useState({
    employeeId: "",
    leaveType: "annual" as const,
    startDate: "",
    endDate: "",
    reason: "",
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (selfService && user?.linkedEmployeeId) {
      setForm((prev) => ({ ...prev, employeeId: String(user.linkedEmployeeId) }));
    }
  }, [selfService, user?.linkedEmployeeId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const employeeId = selfService
      ? Number(user?.linkedEmployeeId)
      : Number(form.employeeId);
    if (!employeeId) {
      setError(
        selfService
          ? "Your login is not linked to an employee record. Ask an admin to link your account."
          : "Select an employee.",
      );
      return;
    }
    try {
      await create.mutateAsync({
        employeeId,
        leaveType: form.leaveType,
        startDate: form.startDate,
        endDate: form.endDate,
        reason: form.reason || undefined,
      });
      setForm((prev) => ({
        ...prev,
        reason: "",
        employeeId: selfService && user?.linkedEmployeeId ? String(user.linkedEmployeeId) : "",
      }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit leave request");
    }
  }

  return (
    <>
      <PageHeader
        title={selfService ? "My leave requests" : "Leave Requests"}
        breadcrumb="Attendance / Leave Requests"
        actions={
          <Link to="/attendance">
            <Button variant="secondary">Overview</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}

        {canSubmit ? (
          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>
              {selfService ? "Request leave" : "Submit leave request"}
            </h2>
            {selfService ? (
              <p
                style={{
                  marginTop: 0,
                  color: "var(--color-text-secondary)",
                  fontSize: "var(--text-sm)",
                }}
              >
                Your request stays pending until HR approves or rejects it. Attendance only changes
                after approval.
              </p>
            ) : null}
            <form
              onSubmit={onSubmit}
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
              }}
            >
              {selfService ? null : (
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
              )}
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
                <Button type="submit" variant="primary" disabled={create.isPending}>
                  {create.isPending ? "Submitting…" : "Submit Leave Request"}
                </Button>
              </div>
            </form>
          </section>
        ) : null}

        {leaves.isLoading ? <Spinner /> : null}
        {leaves.data && leaves.data.items.length === 0 ? (
          <EmptyState
            title={selfService ? "No leave requests yet" : "No leave requests"}
            description={
              selfService
                ? "Submit a leave request above. It will appear here as pending until HR decides."
                : "Submit a leave request. Pending leave does not change attendance until approved."
            }
          />
        ) : null}
        {leaves.data && leaves.data.items.length > 0 ? (
          <>
            <Table
              headers={
                selfService
                  ? ["Type", "From", "To", "Status"]
                  : ["Employee", "Type", "From", "To", "Status", "Actions"]
              }
            >
              {leaves.data.items.map((l) => (
                <tr key={l.id} data-status={l.status === "approved" ? "on_leave" : l.status}>
                  {selfService ? null : <td className="num">{l.employeeId}</td>}
                  <td>{l.leaveType}</td>
                  <td className="num">{l.startDate}</td>
                  <td className="num">{l.endDate}</td>
                  <td>
                    <StatusBadge status={l.status === "approved" ? "on_leave" : l.status}>
                      {LEAVE_STATUS_LABELS[l.status as keyof typeof LEAVE_STATUS_LABELS] ?? l.status}
                    </StatusBadge>
                  </td>
                  {selfService ? null : (
                    <td>
                      <div className="table-actions">
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
                      </div>
                    </td>
                  )}
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
