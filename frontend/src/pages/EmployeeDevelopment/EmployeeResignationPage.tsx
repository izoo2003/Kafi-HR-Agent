import { useState, type FormEvent } from "react";
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
import { useAuth } from "../../hooks/useAuth";
import {
  useEmployeeDevelopmentEmployees,
  useEmployeeDevelopmentSelection,
} from "../../hooks/useEmployeeDevelopmentEmployees";
import {
  useAcceptEmployeeResignation,
  useCreateEmployeeResignation,
  useDeleteEmployeeResignation,
  useEmployeeResignations,
  useGenerateEmployeeResignation,
  useUpdateEmployeeResignation,
} from "../../hooks/useEmployeeResignation";
import type { EmployeeResignation } from "../../types/employeeResignation";

function statusBadge(status: string): string {
  if (status === "accepted") return "approved";
  if (status === "pending") return "pending";
  return "draft";
}

export function EmployeeResignationPage() {
  const { user, hasPermission, logout } = useAuth();
  const navigate = useNavigate();
  const { selfService, canListEmployees, employees } = useEmployeeDevelopmentEmployees();
  const canWrite = hasPermission("kpi", "write") && !selfService && canListEmployees;
  const { employeeId, setEmployeeId } = useEmployeeDevelopmentSelection(
    Boolean(employees.data?.items.length),
    employees.data?.items,
    { selfService, linkedEmployeeId: user?.linkedEmployeeId ?? null },
  );
  const [reason, setReason] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  );
  const [subject, setSubject] = useState("");
  const [letterBody, setLetterBody] = useState("");
  const [viewing, setViewing] = useState<EmployeeResignation | null>(null);
  const [editing, setEditing] = useState<EmployeeResignation | null>(null);
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
  const accept = useAcceptEmployeeResignation();

  async function onGenerate() {
    if (employeeId === "") return;
    setError(null);
    setMessage(null);
    try {
      const res = await generate.mutateAsync({
        employeeId: Number(employeeId),
        reason: reason.trim() || undefined,
        effectiveDate: effectiveDate || undefined,
      });
      setSubject(res.subject);
      setLetterBody(res.letterBody);
      setMessage("Letter generated — review below, then send to the employee.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate letter");
    }
  }

  async function onSend(e: FormEvent) {
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
    const ok = window.confirm(
      "Accept this resignation? Your employment will end, your employee record will be exited, and your login will be removed. This cannot be undone.",
    );
    if (!ok) return;
    setError(null);
    try {
      await accept.mutateAsync(notice.id);
      setViewing(null);
      setMessage("Resignation accepted. Signing you out…");
      await logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not accept resignation");
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
    if (!window.confirm("Delete this resignation notice?")) return;
    setError(null);
    try {
      await remove.mutateAsync(notice.id);
      if (viewing?.id === notice.id) setViewing(null);
      setMessage("Resignation notice deleted.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete notice");
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
          <Card>
            <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              Resignation letters sent to you by HR appear here. Accepting ends your employment and
              removes your login.
            </p>
          </Card>
        ) : canWrite ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Send resignation letter</h2>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              Generate a letter, review it, then send. When the employee accepts on their account,
              they are exited from Employees and their user login is deactivated (hidden from User
              Management).
            </p>
            <form onSubmit={onSend} style={{ display: "grid", gap: "var(--space-3)" }}>
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
            {selfService ? "Your resignation notices" : "Resignation notices"}
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
                  ? "When HR sends you a resignation letter, it will appear here for you to review and accept."
                  : "Generate and send a resignation letter to an employee above."
              }
            />
          ) : null}

          {(list.data?.items.length ?? 0) > 0 ? (
            <Table
              headers={
                selfService
                  ? ["Subject", "Effective", "Status", "Actions"]
                  : ["Employee", "Subject", "Effective", "Status", "Actions"]
              }
            >
              {(list.data?.items ?? []).map((row) => (
                <tr
                  key={row.id}
                  data-status={
                    row.status === "accepted"
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
                  <td>{row.subject}</td>
                  <td className="font-data">{row.effectiveDate ?? "—"}</td>
                  <td>
                    <StatusBadge status={statusBadge(row.status)}>{row.status}</StatusBadge>
                  </td>
                  <td>
                    <div className="table-actions">
                      <Button type="button" variant="secondary" onClick={() => setViewing(row)}>
                        View
                      </Button>
                      {canWrite && row.status === "pending" ? (
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
                      {selfService && row.status === "pending" ? (
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
              Status: {viewing.status}
              {viewing.effectiveDate ? ` · Effective ${viewing.effectiveDate}` : ""}
              {viewing.reason ? ` · ${viewing.reason}` : ""}
            </p>
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
            {selfService && viewing.status === "pending" ? (
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
          </Card>
        ) : null}

        {editing ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Edit resignation notice</h2>
            <form onSubmit={onSaveEdit} style={{ display: "grid", gap: "var(--space-3)" }}>
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
