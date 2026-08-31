import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { ApiError } from "../../api/client";
import { RESIGNATION_STATUS_LABELS } from "../../constants/statusLabels";
import { useAuth } from "../../hooks/useAuth";
import {
  useEmployeeDevelopmentEmployees,
} from "../../hooks/useEmployeeDevelopmentEmployees";
import {
  useAcceptEmployeeResignation,
  useCreateEmployeeResignation,
  useDeleteEmployeeResignation,
  useEmployeeResignations,
  useGenerateEmployeeResignation,
  useRejectEmployeeResignation,
  useSubmitEmployeeResignation,
  useUpdateEmployeeResignation,
  useWithdrawEmployeeResignation,
} from "../../hooks/useEmployeeResignation";
import type { EmployeeResignation, ResignationStatus } from "../../types/employeeResignation";

function statusBadge(status: string): string {
  if (status === "accepted") return "approved";
  if (status === "rejected") return "rejected";
  if (status === "pending") return "pending";
  return "draft";
}

function statusLabel(row: EmployeeResignation): string {
  if (row.status === "pending" && row.direction === "employee") return "Pending HR review";
  if (row.status === "pending" && row.direction === "hr") return "Pending employee";
  return RESIGNATION_STATUS_LABELS[row.status as ResignationStatus] ?? row.status;
}

function fromLabel(row: EmployeeResignation): string {
  return row.direction === "employee" ? "Employee" : "HR";
}

export function EmployeeResignationPage() {
  const { user, hasPermission, logout } = useAuth();
  const navigate = useNavigate();
  const { selfService, canListEmployees, employees } = useEmployeeDevelopmentEmployees();
  const canWrite = hasPermission("kpi", "write") && !selfService && canListEmployees;
  const [employeeId, setEmployeeId] = useState<number | "">("");
  const [reason, setReason] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  );
  const [subject, setSubject] = useState("");
  const [letterBody, setLetterBody] = useState("");
  const [draftId, setDraftId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<EmployeeResignation | null>(null);
  const [editing, setEditing] = useState<EmployeeResignation | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const listEmployeeId = selfService
    ? user?.linkedEmployeeId ?? null
    : employeeId === ""
      ? null
      : Number(employeeId);
  const list = useEmployeeResignations(listEmployeeId, true);
  const generate = useGenerateEmployeeResignation();
  const create = useCreateEmployeeResignation();
  const update = useUpdateEmployeeResignation();
  const remove = useDeleteEmployeeResignation();
  const submit = useSubmitEmployeeResignation();
  const withdraw = useWithdrawEmployeeResignation();
  const accept = useAcceptEmployeeResignation();
  const reject = useRejectEmployeeResignation();

  const myOpen = useMemo(() => {
    if (!selfService) return null;
    return (list.data?.items ?? []).find(
      (r) =>
        r.direction === "employee" &&
        (r.status === "draft" || r.status === "rejected" || r.status === "pending"),
    );
  }, [selfService, list.data?.items]);

  const composingId =
    draftId ??
    (myOpen && (myOpen.status === "draft" || myOpen.status === "rejected") ? myOpen.id : null);

  useEffect(() => {
    if (!selfService || draftId != null || !myOpen) return;
    if (myOpen.status !== "draft" && myOpen.status !== "rejected") return;
    setDraftId(myOpen.id);
    setSubject(myOpen.subject);
    setLetterBody(myOpen.letterBody);
    setReason(myOpen.reason ?? "");
    setEffectiveDate(myOpen.effectiveDate ?? new Date().toISOString().slice(0, 10));
  }, [selfService, myOpen, draftId]);

  function loadMine(row: EmployeeResignation) {
    setDraftId(row.id);
    setSubject(row.subject);
    setLetterBody(row.letterBody);
    setReason(row.reason ?? "");
    setEffectiveDate(row.effectiveDate ?? new Date().toISOString().slice(0, 10));
  }

  function resetComposer() {
    setDraftId(null);
    setSubject("");
    setLetterBody("");
    setReason("");
    setEffectiveDate(new Date().toISOString().slice(0, 10));
  }

  async function onGenerate() {
    if (!selfService && employeeId === "") return;
    setError(null);
    setMessage(null);
    try {
      const res = await generate.mutateAsync({
        employeeId: selfService ? undefined : Number(employeeId),
        reason: reason.trim() || undefined,
        effectiveDate: effectiveDate || undefined,
      });
      setSubject(res.subject);
      setLetterBody(res.letterBody);
      setMessage(
        selfService
          ? "Letter generated — review it, save a draft, or send it to HR."
          : "Letter generated — review below, then send to the employee.",
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate letter");
    }
  }

  async function onSaveDraft() {
    if (!subject.trim() || !letterBody.trim()) return;
    setError(null);
    setMessage(null);
    try {
      if (composingId != null) {
        await update.mutateAsync({
          noticeId: composingId,
          subject: subject.trim(),
          letterBody: letterBody.trim(),
          reason: reason.trim() || null,
          effectiveDate: effectiveDate || null,
        });
        setDraftId(composingId);
        setMessage("Draft saved. Send it to HR when you are ready.");
      } else {
        const row = await create.mutateAsync({
          subject: subject.trim(),
          letterBody: letterBody.trim(),
          reason: reason.trim() || undefined,
          effectiveDate: effectiveDate || undefined,
          submit: false,
        });
        setDraftId(row.id);
        setMessage("Draft saved. Send it to HR when you are ready.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save draft");
    }
  }

  async function onSendToHr(e: FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !letterBody.trim()) return;
    setError(null);
    setMessage(null);
    try {
      if (composingId != null) {
        await update.mutateAsync({
          noticeId: composingId,
          subject: subject.trim(),
          letterBody: letterBody.trim(),
          reason: reason.trim() || null,
          effectiveDate: effectiveDate || null,
        });
        await submit.mutateAsync(composingId);
      } else {
        await create.mutateAsync({
          subject: subject.trim(),
          letterBody: letterBody.trim(),
          reason: reason.trim() || undefined,
          effectiveDate: effectiveDate || undefined,
          submit: true,
        });
      }
      resetComposer();
      setMessage("Resignation letter sent to HR. They will accept or reject it.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send resignation letter");
    }
  }

  async function onSendToEmployee(e: FormEvent) {
    e.preventDefault();
    if (employeeId === "" || !subject.trim() || !letterBody.trim()) return;
    setError(null);
    setMessage(null);
    try {
      await create.mutateAsync({
        employeeId: Number(employeeId),
        subject: subject.trim(),
        letterBody: letterBody.trim(),
        reason: reason.trim() || undefined,
        effectiveDate: effectiveDate || undefined,
      });
      setSubject("");
      setLetterBody("");
      setReason("");
      setMessage("Resignation letter sent. The employee can view and accept it on their account.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send resignation letter");
    }
  }

  async function onAccept(notice: EmployeeResignation) {
    const employeeAcceptingHr = selfService && notice.direction === "hr";
    const ok = window.confirm(
      employeeAcceptingHr
        ? "Accept this resignation? Your employment will end, your employee record will be exited, and your login will be removed. This cannot be undone."
        : "Accept this employee's resignation? Their employment will end and their login will be removed. This cannot be undone.",
    );
    if (!ok) return;
    setError(null);
    try {
      await accept.mutateAsync(notice.id);
      setViewing(null);
      if (employeeAcceptingHr) {
        setMessage("Resignation accepted. Signing you out…");
        await logout();
        navigate("/login", { replace: true });
      } else {
        setMessage("Resignation accepted. The employee has been exited.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not accept resignation");
    }
  }

  async function onReject(notice: EmployeeResignation) {
    setError(null);
    try {
      await reject.mutateAsync({ noticeId: notice.id, reason: rejectReason.trim() || undefined });
      setViewing(null);
      setRejectReason("");
      setMessage("Resignation rejected. The employee can edit and send it again.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject resignation");
    }
  }

  async function onCancel(notice: EmployeeResignation) {
    setError(null);
    try {
      await update.mutateAsync({ noticeId: notice.id, status: "cancelled" });
      setMessage("Resignation notice cancelled.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not cancel notice");
    }
  }

  async function onDelete(notice: EmployeeResignation) {
    if (!window.confirm("Delete this resignation letter?")) return;
    setError(null);
    try {
      await remove.mutateAsync(notice.id);
      if (viewing?.id === notice.id) setViewing(null);
      if (draftId === notice.id) resetComposer();
      setMessage("Resignation letter deleted.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete letter");
    }
  }

  async function onWithdraw(notice: EmployeeResignation) {
    setError(null);
    try {
      const row = await withdraw.mutateAsync(notice.id);
      loadMine(row);
      setMessage("Withdrawn from HR. You can edit it and send it again.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not withdraw letter");
    }
  }

  async function onSaveEdit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setError(null);
    try {
      await update.mutateAsync({
        noticeId: editing.id,
        subject: editing.subject,
        letterBody: editing.letterBody,
        reason: editing.reason,
        effectiveDate: editing.effectiveDate,
      });
      setEditing(null);
      setMessage("Resignation notice updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update notice");
    }
  }

  const employeeCanCompose =
    selfService && (!myOpen || myOpen.status === "draft" || myOpen.status === "rejected");
  const employeeWaiting = selfService && myOpen?.status === "pending";

  return (
    <>
      <PageHeader
        title="Employee Resignation"
        breadcrumb="Employee Development / Employee Resignation"
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        {selfService ? (
          employeeWaiting ? (
            <Card status="warning">
              <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Sent to HR</h2>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Your resignation letter is with HR. They will accept or reject it. Withdraw it if you
                need to make changes first.
              </p>
              {myOpen ? (
                <div style={{ marginTop: "var(--space-3)", display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                  <Button type="button" variant="secondary" onClick={() => setViewing(myOpen)}>
                    View letter
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={withdraw.isPending}
                    onClick={() => void onWithdraw(myOpen)}
                  >
                    {withdraw.isPending ? "Withdrawing…" : "Withdraw and edit"}
                  </Button>
                </div>
              ) : null}
            </Card>
          ) : (
            <Card>
              <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>
                {draftId || myOpen?.status === "rejected" ? "Your resignation letter" : "Create resignation letter"}
              </h2>
              {myOpen?.status === "rejected" ? (
                <p style={{ color: "var(--color-status-critical)", fontSize: "var(--text-sm)" }}>
                  HR rejected this letter
                  {myOpen.rejectionReason ? `: ${myOpen.rejectionReason}` : "."} Edit it and send it
                  again.
                </p>
              ) : (
                <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  Write or generate your resignation letter, save a draft, then send it to HR for
                  accept or reject.
                </p>
              )}
              {employeeCanCompose ? (
                <form onSubmit={(e) => void onSendToHr(e)} style={{ display: "grid", gap: "var(--space-3)" }}>
                  <div
                    style={{
                      display: "grid",
                      gap: "var(--space-3)",
                      gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
                    }}
                  >
                    <FormField
                      label="Last working day"
                      type="date"
                      value={effectiveDate}
                      onChange={(e) => setEffectiveDate(e.target.value)}
                    />
                    <FormField
                      label="Reason"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Optional"
                    />
                  </div>
                  <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={generate.isPending}
                      onClick={() => {
                        if (myOpen && (myOpen.status === "draft" || myOpen.status === "rejected") && !draftId) {
                          loadMine(myOpen);
                        }
                        void onGenerate();
                      }}
                    >
                      {generate.isPending ? "Generating…" : "Generate letter"}
                    </Button>
                    {myOpen && (myOpen.status === "draft" || myOpen.status === "rejected") && !letterBody ? (
                      <Button type="button" variant="secondary" onClick={() => loadMine(myOpen)}>
                        Continue saved letter
                      </Button>
                    ) : null}
                  </div>
                  {subject || letterBody ? (
                    <>
                      <FormField
                        label="Subject"
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        required
                      />
                      <label className="form-field">
                        <span className="form-field__label">Letter</span>
                        <textarea
                          className="form-field__input"
                          rows={12}
                          value={letterBody}
                          onChange={(e) => setLetterBody(e.target.value)}
                          required
                        />
                      </label>
                      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={create.isPending || update.isPending || !letterBody.trim()}
                          onClick={() => void onSaveDraft()}
                        >
                          {create.isPending || update.isPending ? "Saving…" : "Save draft"}
                        </Button>
                        <Button
                          type="submit"
                          disabled={
                            create.isPending || submit.isPending || update.isPending || !letterBody.trim()
                          }
                        >
                          {submit.isPending || create.isPending ? "Sending…" : "Send to HR"}
                        </Button>
                      </div>
                    </>
                  ) : null}
                </form>
              ) : null}
            </Card>
          )
        ) : canWrite ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Send resignation letter</h2>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              Generate a letter, review it, then send. When the employee accepts on their account,
              they are exited from Employees and their user login is deactivated. Employees can also
              write their own letter and send it here for you to accept or reject.
            </p>
            <form onSubmit={(e) => void onSendToEmployee(e)} style={{ display: "grid", gap: "var(--space-3)" }}>
              <div
                style={{
                  display: "grid",
                  gap: "var(--space-3)",
                  gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
                }}
              >
                <label className="form-field">
                  <span className="form-field__label">Employee</span>
                  <select
                    className="form-field__input"
                    value={employeeId === "" ? "" : String(employeeId)}
                    onChange={(e) => {
                      setEmployeeId(e.target.value ? Number(e.target.value) : "");
                      setSubject("");
                      setLetterBody("");
                    }}
                    required
                  >
                    <option value="">Select…</option>
                    {(employees.data?.items ?? []).map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.fullName} ({e.employeeCode})
                      </option>
                    ))}
                  </select>
                </label>
                <FormField
                  label="Effective date"
                  type="date"
                  value={effectiveDate}
                  onChange={(e) => setEffectiveDate(e.target.value)}
                />
                <FormField
                  label="Reason / context"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Optional"
                />
              </div>
              <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={generate.isPending || employeeId === ""}
                  onClick={() => void onGenerate()}
                >
                  {generate.isPending ? "Generating…" : "Generate letter"}
                </Button>
              </div>
              {subject || letterBody ? (
                <>
                  <FormField
                    label="Subject"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    required
                  />
                  <label className="form-field">
                    <span className="form-field__label">Letter</span>
                    <textarea
                      className="form-field__input"
                      rows={12}
                      value={letterBody}
                      onChange={(e) => setLetterBody(e.target.value)}
                      required
                    />
                  </label>
                  <Button type="submit" disabled={create.isPending || !letterBody.trim()}>
                    {create.isPending ? "Sending…" : "Send to employee"}
                  </Button>
                </>
              ) : null}
            </form>
          </Card>
        ) : null}

        <section>
          <h2 style={{ margin: "0 0 var(--space-3)", fontSize: "var(--text-lg)" }}>
            {selfService ? "Your resignation letters" : "Resignation notices"}
          </h2>
          {!selfService && canWrite ? (
            <label className="form-field" style={{ maxWidth: 360, marginBottom: "var(--space-3)" }}>
              <span className="form-field__label">Filter by employee</span>
              <select
                className="form-field__input"
                value={employeeId === "" ? "" : String(employeeId)}
                onChange={(e) => setEmployeeId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">All employees</option>
                {(employees.data?.items ?? []).map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.fullName}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {list.isLoading ? <Spinner label="Loading resignations" /> : null}
          {!list.isLoading && (list.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              title={selfService ? "No resignation letters" : "No resignation notices"}
              description={
                selfService
                  ? "Create a letter above and send it to HR, or wait if HR sends one to you."
                  : "Generate and send a letter to an employee, or wait for an employee to send theirs."
              }
            />
          ) : null}

          {(list.data?.items.length ?? 0) > 0 ? (
            <Table
              headers={
                selfService
                  ? ["From", "Subject", "Effective", "Status", "Actions"]
                  : ["Employee", "From", "Subject", "Effective", "Status", "Actions"]
              }
            >
              {(list.data?.items ?? []).map((row) => (
                <tr
                  key={row.id}
                  data-status={
                    row.status === "accepted"
                      ? "critical"
                      : row.status === "rejected"
                        ? "critical"
                        : row.status === "pending"
                          ? "warning"
                          : "neutral"
                  }
                >
                  {selfService ? null : (
                    <td>
                      {row.employeeName ?? `#${row.employeeId}`}
                      {row.employeeCode ? ` (${row.employeeCode})` : ""}
                    </td>
                  )}
                  <td>{fromLabel(row)}</td>
                  <td>{row.subject}</td>
                  <td className="font-data">{row.effectiveDate ?? "—"}</td>
                  <td>
                    <StatusBadge status={statusBadge(row.status)}>{statusLabel(row)}</StatusBadge>
                  </td>
                  <td>
                    <div className="table-actions">
                      <Button type="button" variant="secondary" onClick={() => setViewing(row)}>
                        View
                      </Button>
                      {selfService &&
                      row.direction === "employee" &&
                      (row.status === "draft" || row.status === "rejected") ? (
                        <>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => {
                              loadMine(row);
                              setViewing(null);
                            }}
                          >
                            Edit
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={() => void onDelete(row)}
                          >
                            Delete
                          </Button>
                        </>
                      ) : null}
                      {selfService && row.direction === "employee" && row.status === "pending" ? (
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={withdraw.isPending}
                          onClick={() => void onWithdraw(row)}
                        >
                          Withdraw
                        </Button>
                      ) : null}
                      {canWrite && row.direction === "hr" && row.status === "pending" ? (
                        <>
                          <Button type="button" variant="secondary" onClick={() => setEditing(row)}>
                            Edit
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => void onCancel(row)}
                          >
                            Cancel
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={() => void onDelete(row)}
                          >
                            Delete
                          </Button>
                        </>
                      ) : null}
                      {canWrite && row.direction === "employee" && row.status === "pending" ? (
                        <>
                          <Button
                            type="button"
                            variant="positive"
                            disabled={accept.isPending}
                            onClick={() => void onAccept(row)}
                          >
                            Accept
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={() => {
                              setViewing(row);
                              setRejectReason("");
                            }}
                          >
                            Reject
                          </Button>
                        </>
                      ) : null}
                      {selfService && row.direction === "hr" && row.status === "pending" ? (
                        <Button
                          type="button"
                          variant="destructive"
                          disabled={accept.isPending}
                          onClick={() => void onAccept(row)}
                        >
                          Accept resignation
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
          ) : null}
        </section>

        {viewing ? (
          <Card>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "var(--space-3)",
                flexWrap: "wrap",
              }}
            >
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>{viewing.subject}</h2>
              <Button type="button" variant="secondary" onClick={() => setViewing(null)}>
                Close
              </Button>
            </div>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
              {fromLabel(viewing)} · {statusLabel(viewing)}
              {viewing.effectiveDate ? ` · Effective ${viewing.effectiveDate}` : ""}
              {viewing.reason ? ` · ${viewing.reason}` : ""}
            </p>
            {viewing.status === "rejected" && viewing.rejectionReason ? (
              <p style={{ color: "var(--color-status-critical)", fontSize: "var(--text-sm)" }}>
                Rejection reason: {viewing.rejectionReason}
              </p>
            ) : null}
            <pre
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "var(--font-ui)",
                fontSize: "var(--text-sm)",
                lineHeight: 1.55,
                margin: 0,
              }}
            >
              {viewing.letterBody}
            </pre>
            {selfService && viewing.direction === "hr" && viewing.status === "pending" ? (
              <div style={{ marginTop: "var(--space-4)" }}>
                <Button
                  type="button"
                  variant="destructive"
                  disabled={accept.isPending}
                  onClick={() => void onAccept(viewing)}
                >
                  Accept resignation
                </Button>
              </div>
            ) : null}
            {canWrite && viewing.direction === "employee" && viewing.status === "pending" ? (
              <div style={{ marginTop: "var(--space-4)", display: "grid", gap: "var(--space-3)" }}>
                <label className="form-field">
                  <span className="form-field__label">Rejection reason (if rejecting)</span>
                  <textarea
                    className="form-field__input"
                    rows={3}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Optional note for the employee"
                  />
                </label>
                <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                  <Button
                    type="button"
                    variant="positive"
                    disabled={accept.isPending}
                    onClick={() => void onAccept(viewing)}
                  >
                    Accept resignation
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={reject.isPending}
                    onClick={() => void onReject(viewing)}
                  >
                    Reject
                  </Button>
                </div>
              </div>
            ) : null}
          </Card>
        ) : null}

        {editing ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Edit resignation notice</h2>
            <form onSubmit={(e) => void onSaveEdit(e)} style={{ display: "grid", gap: "var(--space-3)" }}>
              <FormField
                label="Subject"
                value={editing.subject}
                onChange={(e) => setEditing({ ...editing, subject: e.target.value })}
                required
              />
              <label className="form-field">
                <span className="form-field__label">Letter</span>
                <textarea
                  className="form-field__input"
                  rows={10}
                  value={editing.letterBody}
                  onChange={(e) => setEditing({ ...editing, letterBody: e.target.value })}
                  required
                />
              </label>
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                <Button type="submit" disabled={update.isPending}>
                  Save changes
                </Button>
                <Button type="button" variant="secondary" onClick={() => setEditing(null)}>
                  Close
                </Button>
              </div>
            </form>
          </Card>
        ) : null}
      </div>
    </>
  );
}
