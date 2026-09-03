import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Paperclip, Sparkles } from "lucide-react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { FilePreviewModal, type FilePreviewRequest } from "../../components/domain/FilePreviewModal";
import "./DepartmentManagePage.css";
import { ApiError } from "../../api/client";
import {
  deleteDepartmentDocument,
  downloadDepartmentDocument,
  uploadDepartmentDocuments,
} from "../../api/employees";
import {
  useCreateDepartment,
  useDeleteDepartment,
  useDepartments,
  useGenerateDepartmentAiDraft,
  useUpdateDepartment,
} from "../../hooks/useEmployees";
import { useLocalDraftPersist } from "../../hooks/useLocalDraftPersist";
import { useAuth } from "../../hooks/useAuth";
import { clearLocalDraft, formatDraftRestoredMessage, loadLocalDraft } from "../../lib/localDraft";
import type { Department, DepartmentDocument, DepartmentDocumentKind } from "../../types/employees";

const ATTACH_ACCEPT = "image/png,image/jpeg,image/webp,image/gif,application/pdf,.pdf";
const MAX_FILES_PER_KIND = 8;

function emptyToNull(v: string): string | null {
  const t = v.trim();
  return t ? t : null;
}

function previewText(value: string | null | undefined, max = 160): string {
  const t = (value ?? "").trim();
  if (!t) return "—";
  if (t.length <= max) return t;
  return `${t.slice(0, max).trimEnd()}…`;
}

function textCellStyle(): CSSProperties {
  return {
    maxWidth: 280,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    verticalAlign: "top",
  };
}

function docsFor(dept: Department, kind: DepartmentDocumentKind): DepartmentDocument[] {
  return (dept.documents ?? []).filter((d) => d.kind === kind);
}

function DepartmentCopyField({
  kicker,
  title,
  value,
  onChange,
  placeholder,
  ariaLabel,
  attachLabel,
  onGenerateAi,
  aiPending,
  generateDisabled,
  fileInputId,
  savedDocs,
  pendingFiles,
  onPickFiles,
  onRemovePending,
  onRemoveSaved,
  onPreviewSaved,
  onPreviewPending,
  compact = false,
}: {
  kicker: string;
  title: string;
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
  ariaLabel?: string;
  attachLabel: string;
  onGenerateAi: () => void;
  aiPending: boolean;
  generateDisabled: boolean;
  fileInputId: string;
  savedDocs: DepartmentDocument[];
  pendingFiles: File[];
  onPickFiles: (files: File[]) => void;
  onRemovePending: (index: number) => void;
  onRemoveSaved?: (doc: DepartmentDocument) => void;
  onPreviewSaved?: (doc: DepartmentDocument) => void;
  onPreviewPending: (file: File, index: number) => void;
  compact?: boolean;
}) {
  return (
    <section className={compact ? "dept-copy dept-copy--compact" : "dept-copy"}>
      <div>
        <p className="dept-copy__kicker">{kicker}</p>
        <h3 className="dept-copy__title">{title}</h3>
        <p className="dept-copy__hint">
          Type it here, generate with AI, or attach a PDF/image (up to {MAX_FILES_PER_KIND} files).
        </p>
      </div>
      <div className="dept-copy__actions">
        <Button
          type="button"
          variant="secondary"
          disabled={generateDisabled || aiPending}
          onClick={onGenerateAi}
        >
          <Sparkles size={16} aria-hidden />
          {aiPending ? "Generating…" : "Generate with AI"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => document.getElementById(fileInputId)?.click()}
        >
          <Paperclip size={16} aria-hidden />
          {attachLabel}
        </Button>
        <input
          id={fileInputId}
          className="dept-copy__file-input"
          type="file"
          accept={ATTACH_ACCEPT}
          multiple
          onChange={(e) => {
            const picked = Array.from(e.target.files ?? []);
            e.target.value = "";
            if (picked.length) onPickFiles(picked);
          }}
        />
      </div>
      <textarea
        className="form-field__input dept-copy__textarea"
        rows={compact ? 4 : 6}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel ?? title}
      />
      {savedDocs.length > 0 || pendingFiles.length > 0 ? (
        <ul className="dept-copy__files">
          {savedDocs.map((doc) => (
            <li key={`saved-${doc.id}`}>
              <button type="button" className="dept-copy__file-link" onClick={() => onPreviewSaved?.(doc)}>
                {doc.originalFilename}
              </button>
              {onRemoveSaved ? (
                <>
                  {" "}
                  <Button type="button" variant="destructive" onClick={() => onRemoveSaved(doc)}>
                    Remove
                  </Button>
                </>
              ) : null}
            </li>
          ))}
          {pendingFiles.map((file, index) => (
            <li key={`pending-${file.name}-${index}`}>
              <button
                type="button"
                className="dept-copy__file-link"
                onClick={() => onPreviewPending(file, index)}
              >
                {file.name}
              </button>{" "}
              <span style={{ color: "var(--color-text-muted)" }}>(new)</span>{" "}
              <Button type="button" variant="destructive" onClick={() => onRemovePending(index)}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function DepartmentManagePage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const departments = useDepartments();
  const createDept = useCreateDepartment();
  const updateDept = useUpdateDepartment();
  const deleteDept = useDeleteDepartment();
  const aiDraft = useGenerateDepartmentAiDraft();

  const [deptName, setDeptName] = useState("");
  const [deptJd, setDeptJd] = useState("");
  const [deptSops, setDeptSops] = useState("");
  const [pendingJdFiles, setPendingJdFiles] = useState<File[]>([]);
  const [pendingSopFiles, setPendingSopFiles] = useState<File[]>([]);

  const [editingDeptId, setEditingDeptId] = useState<number | null>(null);
  const [editingDeptName, setEditingDeptName] = useState("");
  const [editingDeptJd, setEditingDeptJd] = useState("");
  const [editingDeptSops, setEditingDeptSops] = useState("");

  const [aiKind, setAiKind] = useState<DepartmentDocumentKind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [draftMessage, setDraftMessage] = useState<string | null>(null);
  const [filePreview, setFilePreview] = useState<FilePreviewRequest | null>(null);
  const restoredRef = useRef(false);

  const draftScope = "department_manage";
  const draftDirty = Boolean(
    deptName.trim() ||
      deptJd.trim() ||
      deptSops.trim() ||
      editingDeptId != null ||
      editingDeptName.trim() ||
      editingDeptJd.trim() ||
      editingDeptSops.trim(),
  );
  useLocalDraftPersist({
    scope: draftScope,
    dirty: draftDirty,
    enabled: canWrite,
    data: {
      deptName,
      deptJd,
      deptSops,
      editingDeptId,
      editingDeptName,
      editingDeptJd,
      editingDeptSops,
    },
    isEmpty: (d) =>
      !d.deptName.trim() &&
      !d.deptJd.trim() &&
      !d.deptSops.trim() &&
      d.editingDeptId == null &&
      !d.editingDeptName.trim() &&
      !d.editingDeptJd.trim() &&
      !d.editingDeptSops.trim(),
  });

  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    const draft = loadLocalDraft<{
      deptName: string;
      deptJd: string;
      deptSops: string;
      editingDeptId: number | null;
      editingDeptName: string;
      editingDeptJd: string;
      editingDeptSops: string;
    }>(draftScope);
    if (!draft?.data) return;
    setDeptName(draft.data.deptName ?? "");
    setDeptJd(draft.data.deptJd ?? "");
    setDeptSops(draft.data.deptSops ?? "");
    setEditingDeptId(draft.data.editingDeptId ?? null);
    setEditingDeptName(draft.data.editingDeptName ?? "");
    setEditingDeptJd(draft.data.editingDeptJd ?? "");
    setEditingDeptSops(draft.data.editingDeptSops ?? "");
    setDraftMessage(formatDraftRestoredMessage(draft.savedAt, "department draft"));
  }, []);

  function clearEdit() {
    setEditingDeptId(null);
    setEditingDeptName("");
    setEditingDeptJd("");
    setEditingDeptSops("");
  }

  function startEdit(d: Department) {
    setEditingDeptId(d.id);
    setEditingDeptName(d.name);
    setEditingDeptJd(d.jobDescriptionText ?? "");
    setEditingDeptSops(d.sopsText ?? "");
    setError(null);
    setMessage(null);
  }

  function takeFiles(
    current: File[],
    incoming: File[],
    alreadySaved: number,
  ): File[] {
    const room = Math.max(0, MAX_FILES_PER_KIND - alreadySaved - current.length);
    return [...current, ...incoming.slice(0, room)];
  }

  async function generateCopy(
    kind: DepartmentDocumentKind,
    name: string,
    currentText: string,
    apply: (text: string) => void,
  ) {
    if (!name.trim()) {
      setError("Enter a department name before generating with AI");
      return;
    }
    if (currentText.trim()) {
      const ok = window.confirm(
        kind === "sop"
          ? "Generate with AI will replace the SOP text. Continue?"
          : "Generate with AI will replace the Job Description. Continue?",
      );
      if (!ok) return;
    }
    setError(null);
    setMessage(null);
    setAiKind(kind);
    try {
      const draft = await aiDraft.mutateAsync({ name: name.trim(), kind });
      apply(draft.text);
      setMessage(
        kind === "sop"
          ? "AI filled the SOP — review before saving."
          : "AI filled the Job Description — review before saving.",
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generate with AI failed");
    } finally {
      setAiKind(null);
    }
  }

  async function uploadPending(departmentId: number, kind: DepartmentDocumentKind, files: File[]) {
    if (!files.length) return;
    await uploadDepartmentDocuments(departmentId, kind, files);
  }

  async function onCreateDept(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setDraftMessage(null);
    try {
      const created = await createDept.mutateAsync({
        name: deptName.trim(),
        jobDescriptionText: emptyToNull(deptJd),
        sopsText: emptyToNull(deptSops),
      });
      await uploadPending(created.id, "job_description", pendingJdFiles);
      await uploadPending(created.id, "sop", pendingSopFiles);
      await departments.refetch();
      setDeptName("");
      setDeptJd("");
      setDeptSops("");
      setPendingJdFiles([]);
      setPendingSopFiles([]);
      clearLocalDraft(draftScope);
      setMessage("Department created — it will appear when creating or editing an employee.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create department");
    }
  }

  async function onSaveDept(id: number) {
    const name = editingDeptName.trim();
    if (!name) {
      setError("Department name cannot be empty.");
      return;
    }
    setError(null);
    setMessage(null);
    setDraftMessage(null);
    try {
      await updateDept.mutateAsync({
        id,
        payload: {
          name,
          jobDescriptionText: emptyToNull(editingDeptJd),
          sopsText: emptyToNull(editingDeptSops),
        },
      });
      clearEdit();
      clearLocalDraft(draftScope);
      setMessage("Department updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update department");
    }
  }

  async function onDeleteDept(id: number, name: string) {
    const ok = window.confirm(
      `Remove department "${name}"?\n\nThis is only allowed if no employees, job descriptions, or attendance rules still use it. Any KPI definitions for this department will be removed with it.`,
    );
    if (!ok) return;
    setError(null);
    setMessage(null);
    try {
      await deleteDept.mutateAsync(id);
      if (editingDeptId === id) clearEdit();
      setMessage(`Department "${name}" removed.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove department");
    }
  }

  async function onRemoveSaved(doc: DepartmentDocument) {
    setError(null);
    try {
      await deleteDepartmentDocument(doc.departmentId, doc.id);
      await departments.refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove attachment");
    }
  }

  async function onUploadSaved(departmentId: number, kind: DepartmentDocumentKind, files: File[]) {
    setError(null);
    try {
      await uploadDepartmentDocuments(departmentId, kind, files);
      await departments.refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not upload attachment");
    }
  }

  function previewSaved(doc: DepartmentDocument) {
    setFilePreview({
      key: `dept-doc-${doc.id}`,
      title: doc.originalFilename,
      filename: doc.originalFilename,
      load: () => downloadDepartmentDocument(doc.departmentId, doc.id),
    });
  }

  function previewPending(file: File, index: number) {
    setFilePreview({
      key: `pending-${file.name}-${index}`,
      title: file.name,
      filename: file.name,
      load: async () => file,
    });
  }

  const tableHeaders = canWrite
    ? ["Department", "Job Description", "SOPs", "Actions"]
    : ["Department", "Job Description", "SOPs"];

  return (
    <>
      <PageHeader title="Departments" breadcrumb="Organization / Employees Management / Departments" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          Create departments with their job description and SOPs. These are the roles you assign on
          employee records. You can generate the text with AI and attach a PDF or image to either
          field.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}
        {draftMessage ? <p style={{ color: "var(--color-status-warning)" }}>{draftMessage}</p> : null}

        {canWrite ? (
          <Card>
            <form onSubmit={onCreateDept} style={{ display: "grid", gap: "var(--space-4)" }}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Create Department</h2>
              <FormField
                label="Department name"
                value={deptName}
                onChange={(e) => setDeptName(e.target.value)}
                required
              />
              <div className="dept-copy-grid">
                <DepartmentCopyField
                  kicker="JD"
                  title="Job Description"
                  value={deptJd}
                  onChange={setDeptJd}
                  placeholder="Duties and responsibilities for this department role…"
                  attachLabel="Attach JD file"
                  onGenerateAi={() => void generateCopy("job_description", deptName, deptJd, setDeptJd)}
                  aiPending={aiDraft.isPending && aiKind === "job_description"}
                  generateDisabled={!deptName.trim() || aiDraft.isPending}
                  fileInputId="create-jd-files"
                  savedDocs={[]}
                  pendingFiles={pendingJdFiles}
                  onPickFiles={(files) =>
                    setPendingJdFiles((current) => takeFiles(current, files, 0))
                  }
                  onRemovePending={(index) =>
                    setPendingJdFiles((current) => current.filter((_, i) => i !== index))
                  }
                  onPreviewPending={previewPending}
                />
                <DepartmentCopyField
                  kicker="SOPs"
                  title="Standard Operating Procedures"
                  value={deptSops}
                  onChange={setDeptSops}
                  placeholder="Standard operating procedures for this department…"
                  attachLabel="Attach SOP file"
                  onGenerateAi={() => void generateCopy("sop", deptName, deptSops, setDeptSops)}
                  aiPending={aiDraft.isPending && aiKind === "sop"}
                  generateDisabled={!deptName.trim() || aiDraft.isPending}
                  fileInputId="create-sop-files"
                  savedDocs={[]}
                  pendingFiles={pendingSopFiles}
                  onPickFiles={(files) =>
                    setPendingSopFiles((current) => takeFiles(current, files, 0))
                  }
                  onRemovePending={(index) =>
                    setPendingSopFiles((current) => current.filter((_, i) => i !== index))
                  }
                  onPreviewPending={previewPending}
                />
              </div>
              <div>
                <Button type="submit" variant="primary" disabled={createDept.isPending}>
                  {createDept.isPending ? "Creating…" : "Create Department"}
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        {departments.isLoading ? <Spinner label="Loading departments" /> : null}
        {(departments.data ?? []).length === 0 && !departments.isLoading ? (
          <EmptyState
            title="No departments yet"
            description="Create a department above with its job description and SOPs. Employees pick one as their role."
          />
        ) : (
          <Table headers={tableHeaders}>
            {(departments.data ?? []).map((d) => {
              const isEditing = editingDeptId === d.id;
              const jdDocs = docsFor(d, "job_description");
              const sopDocs = docsFor(d, "sop");
              return (
                <tr key={d.id}>
                  <td style={{ verticalAlign: "top", minWidth: 160 }}>
                    {isEditing ? (
                      <input
                        className="form-field__input"
                        value={editingDeptName}
                        onChange={(e) => setEditingDeptName(e.target.value)}
                        aria-label={`Rename ${d.name}`}
                      />
                    ) : (
                      d.name
                    )}
                  </td>
                  <td style={textCellStyle()}>
                    {isEditing ? (
                      <DepartmentCopyField
                        kicker="JD"
                        title="Job Description"
                        value={editingDeptJd}
                        onChange={setEditingDeptJd}
                        placeholder="Duties and responsibilities…"
                        ariaLabel={`Job description for ${d.name}`}
                        attachLabel="Attach JD file"
                        compact
                        onGenerateAi={() =>
                          void generateCopy(
                            "job_description",
                            editingDeptName,
                            editingDeptJd,
                            setEditingDeptJd,
                          )
                        }
                        aiPending={aiDraft.isPending && aiKind === "job_description"}
                        generateDisabled={!editingDeptName.trim() || aiDraft.isPending}
                        fileInputId={`edit-jd-files-${d.id}`}
                        savedDocs={jdDocs}
                        pendingFiles={[]}
                        onPickFiles={(files) => void onUploadSaved(d.id, "job_description", files)}
                        onRemovePending={() => undefined}
                        onRemoveSaved={onRemoveSaved}
                        onPreviewSaved={previewSaved}
                        onPreviewPending={previewPending}
                      />
                    ) : (
                      <>
                        <div>{previewText(d.jobDescriptionText)}</div>
                        {jdDocs.length > 0 ? (
                          <div style={{ marginTop: "var(--space-2)" }}>
                            {jdDocs.map((doc) => (
                              <div key={doc.id}>
                                <button
                                  type="button"
                                  onClick={() => previewSaved(doc)}
                                  style={{
                                    background: "none",
                                    border: 0,
                                    padding: 0,
                                    color: "var(--color-accent)",
                                    cursor: "pointer",
                                    textDecoration: "underline",
                                    fontSize: "var(--text-sm)",
                                  }}
                                >
                                  {doc.originalFilename}
                                </button>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </>
                    )}
                  </td>
                  <td style={textCellStyle()}>
                    {isEditing ? (
                      <DepartmentCopyField
                        kicker="SOPs"
                        title="Standard Operating Procedures"
                        value={editingDeptSops}
                        onChange={setEditingDeptSops}
                        placeholder="Standard operating procedures…"
                        ariaLabel={`SOPs for ${d.name}`}
                        attachLabel="Attach SOP file"
                        compact
                        onGenerateAi={() =>
                          void generateCopy("sop", editingDeptName, editingDeptSops, setEditingDeptSops)
                        }
                        aiPending={aiDraft.isPending && aiKind === "sop"}
                        generateDisabled={!editingDeptName.trim() || aiDraft.isPending}
                        fileInputId={`edit-sop-files-${d.id}`}
                        savedDocs={sopDocs}
                        pendingFiles={[]}
                        onPickFiles={(files) => void onUploadSaved(d.id, "sop", files)}
                        onRemovePending={() => undefined}
                        onRemoveSaved={onRemoveSaved}
                        onPreviewSaved={previewSaved}
                        onPreviewPending={previewPending}
                      />
                    ) : (
                      <>
                        <div>{previewText(d.sopsText)}</div>
                        {sopDocs.length > 0 ? (
                          <div style={{ marginTop: "var(--space-2)" }}>
                            {sopDocs.map((doc) => (
                              <div key={doc.id}>
                                <button
                                  type="button"
                                  onClick={() => previewSaved(doc)}
                                  style={{
                                    background: "none",
                                    border: 0,
                                    padding: 0,
                                    color: "var(--color-accent)",
                                    cursor: "pointer",
                                    textDecoration: "underline",
                                    fontSize: "var(--text-sm)",
                                  }}
                                >
                                  {doc.originalFilename}
                                </button>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </>
                    )}
                  </td>
                  {canWrite ? (
                    <td className="col-actions" style={{ verticalAlign: "top" }}>
                      <div
                        className="table-actions"
                        style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}
                      >
                        {isEditing ? (
                          <>
                            <Button
                              type="button"
                              variant="primary"
                              disabled={updateDept.isPending}
                              onClick={() => onSaveDept(d.id)}
                            >
                              Save
                            </Button>
                            <Button type="button" variant="secondary" onClick={clearEdit}>
                              Cancel
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button type="button" variant="secondary" onClick={() => startEdit(d)}>
                              Edit
                            </Button>
                            <Button
                              type="button"
                              variant="destructive"
                              disabled={deleteDept.isPending}
                              onClick={() => onDeleteDept(d.id, d.name)}
                            >
                              Remove
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  ) : null}
                </tr>
              );
            })}
          </Table>
        )}

        <div>
          <Link to="/employees">
            <Button type="button" variant="secondary">
              Back to employees
            </Button>
          </Link>
        </div>
      </div>
      {filePreview ? (
        <FilePreviewModal preview={filePreview} onClose={() => setFilePreview(null)} />
      ) : null}
    </>
  );
}
