import { useEffect, useRef, useState, type FormEvent } from "react";
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
import { useLocalDraftPersist } from "../../hooks/useLocalDraftPersist";
import { LEAVE_STATUS_LABELS, LEAVE_TYPE_LABELS } from "../../constants/statusLabels";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import {
  clearLocalDraft,
  formatDraftRestoredMessage,
  loadLocalDraft,
} from "../../lib/localDraft";
import { isSelfService } from "../../lib/selfService";
import "./LeaveRequestsPage.css";

type LeaveForm = {
  employeeId: string;
  leaveType: "annual" | "sick" | "unpaid" | "other";
  startDate: string;
  endDate: string;
  reason: string;
};

const EMPTY_LEAVE_FORM: LeaveForm = {
  employeeId: "",
  leaveType: "annual",
  startDate: "",
  endDate: "",
  reason: "",
};

function leaveFormIsMeaningful(data: LeaveForm): boolean {
  return Boolean(data.startDate || data.endDate || data.reason.trim());
}

export function LeaveRequestsPage() {
  const { hasPermission, user, loading: authLoading } = useAuth();
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

  const draftScope =
    user?.userId != null ? `leave_request_form:${user.userId}` : "leave_request_form";
  const draftRestoredRef = useRef(false);

  const [form, setForm] = useState<LeaveForm>(EMPTY_LEAVE_FORM);
  const [error, setError] = useState<string | null>(null);
  const [draftMessage, setDraftMessage] = useState<string | null>(null);

  const formDirty = leaveFormIsMeaningful(form);
  useLocalDraftPersist({
    scope: draftScope,
    dirty: formDirty,
    data: form,
    enabled: canSubmit,
    isEmpty: (d) => !leaveFormIsMeaningful(d),
  });

  useEffect(() => {
    if (authLoading || draftRestoredRef.current) return;
    draftRestoredRef.current = true;
    const draft = loadLocalDraft<LeaveForm>(draftScope);
    if (!draft?.data) return;
    setForm({
      ...EMPTY_LEAVE_FORM,
      ...draft.data,
      leaveType: draft.data.leaveType ?? "annual",
      employeeId:
        selfService && user?.linkedEmployeeId
          ? String(user.linkedEmployeeId)
          : (draft.data.employeeId ?? ""),
    });
    setDraftMessage(formatDraftRestoredMessage(draft.savedAt, "leave request draft"));
  }, [authLoading, draftScope, selfService, user?.linkedEmployeeId]);

  useEffect(() => {
    if (selfService && user?.linkedEmployeeId) {
      setForm((prev) => ({ ...prev, employeeId: String(user.linkedEmployeeId) }));
    }
  }, [selfService, user?.linkedEmployeeId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setDraftMessage(null);
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
        reason: form.reason.trim() || undefined,
      });
      clearLocalDraft(draftScope);
      setForm({
        ...EMPTY_LEAVE_FORM,
        employeeId:
          selfService && user?.linkedEmployeeId ? String(user.linkedEmployeeId) : "",
      });
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
        {draftMessage ? <p style={{ color: "var(--color-status-warning)" }}>{draftMessage}</p> : null}

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
            <form onSubmit={onSubmit} className="leave-form">
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
              <label className="form-field leave-form__reason">
                <span className="form-field__label">Reason / notes</span>
                <textarea
                  className="form-field__input"
                  value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  placeholder="Why is this leave needed? Admins see this note, not only the leave type."
                  rows={3}
                />
              </label>
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
                  ? ["Type", "From", "To", "Reason", "Status"]
                  : ["Employee", "Type", "From", "To", "Reason", "Status", "Actions"]
              }
            >
              {leaves.data.items.map((l) => (
                <tr key={l.id} data-status={l.status === "approved" ? "on_leave" : l.status}>
                  {selfService ? null : (
                    <td>
                      {l.employeeName ?? `Employee #${l.employeeId}`}
                      {l.employeeCode ? ` (${l.employeeCode})` : ""}
                    </td>
                  )}
                  <td>
                    {LEAVE_TYPE_LABELS[l.leaveType as keyof typeof LEAVE_TYPE_LABELS] ?? l.leaveType}
                  </td>
                  <td className="num">{l.startDate}</td>
                  <td className="num">{l.endDate}</td>
                  <td>
                    {l.reason?.trim() ? (
                      <span className="leave-reason">{l.reason}</span>
                    ) : (
                      <span className="leave-reason leave-reason--empty">No reason given</span>
                    )}
                  </td>
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
