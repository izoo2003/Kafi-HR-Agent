import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { StatusBadge } from "../../components/ui/Badge";
import { Pagination } from "../../components/ui/Pagination";
import { useAuth } from "../../hooks/useAuth";
import { useDepartments, useEmployees } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import {
  createEmployeeLetter,
  getEmployeeLetterContent,
  saveEmployeeLetterContent,
  verifyEmployeeLetterSignature,
  viewEmployeeLetter,
} from "../../api/employees";
import { ApiError } from "../../api/client";
import { useLocalDraftPersist } from "../../hooks/useLocalDraftPersist";
import { clearLocalDraft, formatDraftRestoredMessage, loadLocalDraft } from "../../lib/localDraft";
import type { Employee } from "../../types/employees";

type LetterKind = "appointment" | "contract";

const VERIFY_ACCEPT =
  "application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg";

const COPY: Record<
  LetterKind,
  { title: string; breadcrumb: string; file: string; empty: string; createLabel: string }
> = {
  appointment: {
    title: "Appointment letters",
    breadcrumb: "Organization / Employees Management / Appointment letter",
    file: "Appointment_Letter",
    empty: "No employees yet. Add an employee first, then create their appointment letter here.",
    createLabel: "Create letter",
  },
  contract: {
    title: "Contract letters",
    breadcrumb: "Organization / Employees Management / Contract letter",
    file: "Employment_Contract",
    empty: "No employees yet. Add an employee first, then create their contract letter here.",
    createLabel: "Create letter",
  },
};

function hasLetter(emp: Employee, kind: LetterKind): boolean {
  return kind === "appointment" ? Boolean(emp.hasAppointmentLetter) : Boolean(emp.hasContractLetter);
}

function isVerified(emp: Employee, kind: LetterKind): boolean {
  return kind === "appointment"
    ? Boolean(emp.appointmentLetterVerified)
    : Boolean(emp.contractLetterVerified);
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function fileName(kind: LetterKind, emp: Employee) {
  const safe = emp.fullName.replace(/[^\w\-]+/g, "_");
  return `${COPY[kind].file}_${safe}.docx`;
}

function isVerifyFile(file: File): boolean {
  const type = (file.type || "").toLowerCase();
  if (type === "application/pdf" || type.startsWith("image/")) return true;
  return /\.(pdf|png|jpe?g)$/i.test(file.name);
}

function isPdfFile(file: File): boolean {
  return (file.type || "").toLowerCase() === "application/pdf" || /\.pdf$/i.test(file.name);
}

export function EmployeeLettersPage({ kind }: { kind: LetterKind }) {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const { page, pageSize, setPage, params } = usePagination(1, 100);
  const [statusFilter, setStatusFilter] = useState<"active" | "terminated" | "all">("active");
  const departments = useDepartments();
  const employees = useEmployees({
    ...params,
    status: statusFilter === "all" ? undefined : statusFilter,
  });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [verifyFor, setVerifyFor] = useState<Employee | null>(null);
  const [verifyPreview, setVerifyPreview] = useState<string | null>(null);
  const [verifyFile, setVerifyFile] = useState<File | null>(null);
  const verifyInputRef = useRef<HTMLInputElement>(null);
  const [editFor, setEditFor] = useState<Employee | null>(null);
  const [editParagraphs, setEditParagraphs] = useState<string[]>([]);
  const [editFilename, setEditFilename] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [draftMessage, setDraftMessage] = useState<string | null>(null);
  const copy = COPY[kind];

  const deptNameById = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  const editDraftScope = editFor ? `employee_letter:${kind}:${editFor.id}` : "";
  useLocalDraftPersist({
    scope: editDraftScope,
    dirty: Boolean(editFor && editParagraphs.some((p) => p.trim()) ),
    enabled: Boolean(editFor),
    data: { paragraphs: editParagraphs, filename: editFilename },
    isEmpty: (d) => !(d.paragraphs ?? []).some((p: string) => p.trim()),
  });

  useEffect(() => {
    if (!editFor) setDraftMessage(null);
  }, [editFor]);

  function closeVerify() {
    if (verifyPreview) URL.revokeObjectURL(verifyPreview);
    setVerifyPreview(null);
    setVerifyFile(null);
    setVerifyFor(null);
    if (verifyInputRef.current) verifyInputRef.current.value = "";
  }

  function openVerify(emp: Employee) {
    setError(null);
    setMessage(null);
    closeVerify();
    closeEdit();
    setVerifyFor(emp);
  }

  function closeEdit() {
    setDraftMessage(null);
    setEditFor(null);
    setEditParagraphs([]);
    setEditFilename("");
    setEditLoading(false);
    setEditSaving(false);
  }

  async function openEdit(emp: Employee) {
    if (!hasLetter(emp, kind)) {
      setError("It is not created yet. Create them first.");
      return;
    }
    setError(null);
    setMessage(null);
    closeVerify();
    setEditFor(emp);
    setEditLoading(true);
    setEditParagraphs([]);
    try {
      const content = await getEmployeeLetterContent(emp.id, kind);
      const restored = loadLocalDraft<{ paragraphs: string[]; filename: string }>(
        `employee_letter:${kind}:${emp.id}`,
      );
      setEditParagraphs(
        restored?.data?.paragraphs?.length
          ? restored.data.paragraphs
          : content.paragraphs.length
            ? content.paragraphs
            : [""],
      );
      if (restored?.data) {
        setDraftMessage(formatDraftRestoredMessage(restored.savedAt, "letter draft"));
      }
      setEditFilename(content.filename);
    } catch (err) {
      closeEdit();
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not open the letter for editing.",
      );
    } finally {
      setEditLoading(false);
    }
  }

  function onPickVerifyFile(file: File | null) {
    if (verifyPreview) URL.revokeObjectURL(verifyPreview);
    setVerifyPreview(null);
    setVerifyFile(null);
    setError(null);
    if (!file) return;
    if (!isVerifyFile(file)) {
      setError("Upload a PDF or image of the signed letter (PDF, PNG, or JPG).");
      return;
    }
    setVerifyFile(file);
    if (!isPdfFile(file)) {
      setVerifyPreview(URL.createObjectURL(file));
    }
  }

  async function onCreate(emp: Employee) {
    setError(null);
    setMessage(null);
    setBusyId(emp.id);
    try {
      const blob = await createEmployeeLetter(emp.id, kind);
      downloadBlob(blob, fileName(kind, emp));
      setMessage(`${copy.createLabel} created for ${emp.fullName}.`);
      await employees.refetch();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not create the letter.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function onDownload(emp: Employee) {
    if (!hasLetter(emp, kind)) {
      setError("It is not created yet. Create them first.");
      return;
    }
    setError(null);
    setBusyId(emp.id);
    try {
      const blob = await viewEmployeeLetter(emp.id, kind);
      downloadBlob(blob, fileName(kind, emp));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "It is not created yet. Create them first.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function onSaveEdit() {
    if (!editFor) return;
    const cleaned = editParagraphs.map((p) => p.replace(/\r/g, ""));
    if (!cleaned.some((p) => p.trim())) {
      setError("Letter content cannot be empty.");
      return;
    }
    setError(null);
    setMessage(null);
    setEditSaving(true);
    try {
      const saved = await saveEmployeeLetterContent(editFor.id, kind, cleaned);
      clearLocalDraft(`employee_letter:${kind}:${editFor.id}`);
      setEditParagraphs(saved.paragraphs.length ? saved.paragraphs : [""]);
      setEditFilename(saved.filename);
      setMessage(`Letter saved for ${editFor.fullName}.`);
      setDraftMessage(null);
      await employees.refetch();
      const blob = await viewEmployeeLetter(editFor.id, kind);
      downloadBlob(blob, fileName(kind, editFor));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not save letter edits.",
      );
    } finally {
      setEditSaving(false);
    }
  }

  async function onSubmitVerify() {
    if (!verifyFor || !verifyFile) {
      setError("Choose a PDF or image of the signed letter first.");
      return;
    }
    setError(null);
    setMessage(null);
    setBusyId(verifyFor.id);
    try {
      const res = await verifyEmployeeLetterSignature(verifyFor.id, kind, verifyFile);
      if (res.verified) {
        setMessage(
          `Verified — ${kind === "appointment" ? "appointment letter" : "employment contract"} identified and signature found for ${verifyFor.fullName}.`,
        );
        closeVerify();
        await employees.refetch();
      } else {
        setError(res.message || "Signature not verified.");
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not verify the signed letter.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader title={copy.title} breadcrumb={copy.breadcrumb} />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Select an employee to create or edit their{" "}
          {kind === "appointment" ? "appointment letter" : "contract letter"}. After the letter is
          created, use <strong>Edit letter</strong> to change the wording in-app,{" "}
          <strong>Upload &amp; Verify</strong> (PDF or PNG/JPG of the signed copy), or{" "}
          <strong>Create letter</strong> again. AI checks that the upload is the correct letter{" "}
          <em>and</em> that a handwritten signature is present. Both must pass for the status to
          become <strong>Verified</strong>.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-info)" }}>{message}</p> : null}
        {draftMessage ? <p style={{ color: "var(--color-status-warning)" }}>{draftMessage}</p> : null}

        <label className="form-field" style={{ maxWidth: 220 }}>
          <span className="form-field__label">Show</span>
          <select
            className="form-field__input"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as "active" | "terminated" | "all");
              setPage(1);
            }}
          >
            <option value="active">Active only</option>
            <option value="terminated">Terminated only</option>
            <option value="all">All</option>
          </select>
        </label>

        {employees.isLoading ? <Spinner label="Loading employees" /> : null}
        {employees.data && employees.data.items.length === 0 ? (
          <EmptyState title="No employees found" description={copy.empty} />
        ) : null}
        {employees.data && employees.data.items.length > 0 ? (
          <>
            <Table headers={["Code", "Name", "Role", "Letter", "Actions"]}>
              {employees.data.items.map((emp) => {
                const created = hasLetter(emp, kind);
                const verified = isVerified(emp, kind);
                const busy = busyId === emp.id;
                const rowStatus = verified ? "info" : created ? "positive" : "neutral";
                const badgeStatus = verified ? "verified" : created ? "approved" : "draft";
                const badgeLabel = verified ? "Verified" : created ? "Created" : "Not created";
                return (
                  <tr key={emp.id} data-status={rowStatus}>
                    <td className="num">{emp.employeeCode}</td>
                    <td>{emp.fullName}</td>
                    <td>{deptNameById(emp.departmentId)}</td>
                    <td>
                      <StatusBadge status={badgeStatus}>{badgeLabel}</StatusBadge>
                    </td>
                    <td className="col-actions">
                      <div
                        className="table-actions"
                        style={{
                          justifyContent: "flex-end",
                          flexWrap: "wrap",
                          maxWidth: 320,
                        }}
                      >
                        {created ? (
                          <>
                            <Button
                              type="button"
                              variant="secondary"
                              disabled={busy || editLoading}
                              onClick={() => void openEdit(emp)}
                            >
                              Edit letter
                            </Button>
                            {canWrite ? (
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={busy || emp.status === "terminated"}
                                onClick={() => openVerify(emp)}
                              >
                                Upload &amp; Verify
                              </Button>
                            ) : null}
                            {canWrite ? (
                              <Button
                                type="button"
                                variant="primary"
                                disabled={busy || emp.status === "terminated"}
                                onClick={() => void onCreate(emp)}
                                style={{ flexBasis: "100%" }}
                              >
                                {busy && verifyFor?.id !== emp.id ? "Working…" : "Create letter"}
                              </Button>
                            ) : null}
                          </>
                        ) : canWrite ? (
                          <Button
                            type="button"
                            variant="primary"
                            disabled={busy || emp.status === "terminated"}
                            onClick={() => void onCreate(emp)}
                          >
                            {busy ? "Working…" : copy.createLabel}
                          </Button>
                        ) : (
                          <Button type="button" variant="secondary" disabled>
                            Edit letter
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={employees.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}

        {editFor ? (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="letter-edit-title"
            onClick={closeEdit}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(16, 24, 40, 0.45)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "var(--space-5)",
              zIndex: 50,
            }}
          >
            <div
              className="card"
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "min(800px, 100%)",
                maxHeight: "min(920px, 92vh)",
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateRows: "auto auto 1fr auto",
                boxShadow: "0 8px 24px rgba(16,24,40,0.12)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "var(--space-3)",
                  alignItems: "center",
                }}
              >
                <h2 id="letter-edit-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                  Edit letter — {editFor.fullName}
                </h2>
                <Button type="button" variant="secondary" onClick={closeEdit}>
                  Close
                </Button>
              </div>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Edit the letter wording below
                {editFilename ? (
                  <>
                    {" "}
                    (<span className="font-data">{editFilename}</span>)
                  </>
                ) : null}
                . Saving updates the stored Word letter
                {canWrite ? " and downloads the revised file" : ""}.
              </p>
              {editLoading ? (
                <Spinner label="Loading letter" />
              ) : (
                <div
                  style={{
                    overflowY: "auto",
                    display: "grid",
                    gap: "var(--space-2)",
                    minHeight: 0,
                    paddingRight: 2,
                  }}
                >
                  {editParagraphs.map((para, index) => (
                    <label key={`p-${index}`} className="form-field" style={{ margin: 0 }}>
                      <span className="form-field__label">Paragraph {index + 1}</span>
                      <textarea
                        className="form-field__input"
                        rows={Math.min(8, Math.max(2, para.split("\n").length + 1))}
                        value={para}
                        readOnly={!canWrite || editFor.status === "terminated"}
                        onChange={(e) => {
                          const next = [...editParagraphs];
                          next[index] = e.target.value;
                          setEditParagraphs(next);
                        }}
                        aria-label={`Letter paragraph ${index + 1}`}
                      />
                    </label>
                  ))}
                  {canWrite && editFor.status !== "terminated" ? (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => setEditParagraphs((prev) => [...prev, ""])}
                    >
                      Add paragraph
                    </Button>
                  ) : null}
                </div>
              )}
              <div
                style={{
                  display: "flex",
                  gap: "var(--space-2)",
                  justifyContent: "flex-end",
                  flexWrap: "wrap",
                }}
              >
                <Button type="button" variant="secondary" onClick={closeEdit}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={editLoading || editSaving || busyId === editFor.id}
                  onClick={() => void onDownload(editFor)}
                >
                  Download Word
                </Button>
                {canWrite && editFor.status !== "terminated" ? (
                  <Button
                    type="button"
                    variant="primary"
                    disabled={editLoading || editSaving}
                    onClick={() => void onSaveEdit()}
                  >
                    {editSaving ? "Saving…" : "Save letter"}
                  </Button>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}

        {verifyFor ? (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="letter-verify-title"
            onClick={closeVerify}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(16, 24, 40, 0.45)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "var(--space-5)",
              zIndex: 50,
            }}
          >
            <div
              className="card"
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "min(560px, 100%)",
                display: "grid",
                gap: "var(--space-3)",
                boxShadow: "0 8px 24px rgba(16,24,40,0.12)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "var(--space-3)",
                  alignItems: "center",
                }}
              >
                <h2 id="letter-verify-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                  Upload &amp; Verify — {verifyFor.fullName}
                </h2>
                <Button type="button" variant="secondary" onClick={closeVerify}>
                  Close
                </Button>
              </div>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Upload a PDF or clear photo (PNG / JPG) of the printed{" "}
                {kind === "appointment" ? "appointment letter" : "employment contract"} with a
                handwritten signature. AI rejects the upload if this is the wrong document type, or
                if no signature is visible.
              </p>
              <label className="form-field">
                <span className="form-field__label">Signed letter (PDF, PNG, or JPG)</span>
                <input
                  ref={verifyInputRef}
                  className="form-field__input"
                  type="file"
                  accept={VERIFY_ACCEPT}
                  onChange={(e) => onPickVerifyFile(e.target.files?.[0] ?? null)}
                />
              </label>
              {verifyFile && isPdfFile(verifyFile) ? (
                <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  Selected PDF: <strong>{verifyFile.name}</strong>
                </p>
              ) : null}
              {verifyPreview ? (
                <img
                  src={verifyPreview}
                  alt="Signed letter preview"
                  style={{
                    display: "block",
                    maxWidth: "100%",
                    maxHeight: 280,
                    margin: "0 auto",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-sm)",
                  }}
                />
              ) : null}
              <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
                <Button type="button" variant="secondary" onClick={closeVerify}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  disabled={!verifyFile || busyId === verifyFor.id}
                  onClick={() => void onSubmitVerify()}
                >
                  {busyId === verifyFor.id ? "Verifying…" : "Upload & Verify"}
                </Button>
              </div>
            </div>
          </div>
        ) : null}

        <div>
          <Link to="/employees">
            <Button type="button" variant="secondary">
              Back to employees
            </Button>
          </Link>
        </div>
      </div>
    </>
  );
}
