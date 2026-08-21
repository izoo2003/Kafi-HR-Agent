import { useMemo, useRef, useState } from "react";
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
  verifyEmployeeLetterSignature,
  viewEmployeeLetter,
} from "../../api/employees";
import { ApiError } from "../../api/client";
import type { Employee } from "../../types/employees";

type LetterKind = "appointment" | "contract";

const IMAGE_ACCEPT =
  "image/png,image/jpeg,image/webp,image/gif,image/heic,image/heif,.png,.jpg,.jpeg,.webp,.gif,.heic,.heif";

const COPY: Record<
  LetterKind,
  { title: string; breadcrumb: string; file: string; empty: string; createLabel: string }
> = {
  appointment: {
    title: "Appointment letters",
    breadcrumb: "Organization / Employees / Appointment letter",
    file: "Appointment_Letter",
    empty: "No employees yet. Add an employee first, then create their appointment letter here.",
    createLabel: "Create appointment letter",
  },
  contract: {
    title: "Contract letters",
    breadcrumb: "Organization / Employees / Contract letter",
    file: "Employment_Contract",
    empty: "No employees yet. Add an employee first, then create their contract letter here.",
    createLabel: "Create contract letter",
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

function isImageFile(file: File): boolean {
  if (file.type.startsWith("image/")) return true;
  return /\.(png|jpe?g|webp|gif|heic|heif)$/i.test(file.name);
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
  const copy = COPY[kind];

  const deptNameById = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

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
    setVerifyFor(emp);
  }

  function onPickVerifyFile(file: File | null) {
    if (verifyPreview) URL.revokeObjectURL(verifyPreview);
    setVerifyPreview(null);
    setVerifyFile(null);
    setError(null);
    if (!file) return;
    if (!isImageFile(file)) {
      setError("Upload an image of the signed letter (PNG, JPG, WEBP, GIF, HEIC) — not a PDF.");
      return;
    }
    setVerifyFile(file);
    setVerifyPreview(URL.createObjectURL(file));
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

  async function onView(emp: Employee) {
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

  async function onSubmitVerify() {
    if (!verifyFor || !verifyFile) {
      setError("Choose an image of the signed letter first.");
      return;
    }
    setError(null);
    setMessage(null);
    setBusyId(verifyFor.id);
    try {
      const res = await verifyEmployeeLetterSignature(verifyFor.id, kind, verifyFile);
      if (res.verified) {
        setMessage(`Verified — signature found on ${verifyFor.fullName}'s letter.`);
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
          Select an employee to create or view their{" "}
          {kind === "appointment" ? "appointment letter" : "contract letter"}. After create, use{" "}
          <strong>Verify</strong> to upload a photo of the signed document — AI checks for a
          signature, then the status becomes <strong>Verified</strong>.
        </p>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-info)" }}>{message}</p> : null}

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
                      <div className="table-actions" style={{ justifyContent: "flex-end" }}>
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={busy || !created}
                          onClick={() => void onView(emp)}
                        >
                          View letter
                        </Button>
                        {canWrite && created ? (
                          <Button
                            type="button"
                            variant="secondary"
                            disabled={busy || emp.status === "terminated"}
                            onClick={() => openVerify(emp)}
                          >
                            {verified ? "Re-verify" : "Verify"}
                          </Button>
                        ) : null}
                        {canWrite ? (
                          <Button
                            type="button"
                            variant="primary"
                            disabled={busy || emp.status === "terminated"}
                            onClick={() => void onCreate(emp)}
                          >
                            {busy && verifyFor?.id !== emp.id
                              ? "Working…"
                              : created
                                ? "Recreate letter"
                                : copy.createLabel}
                          </Button>
                        ) : null}
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
                  Verify signed letter — {verifyFor.fullName}
                </h2>
                <Button type="button" variant="secondary" onClick={closeVerify}>
                  Close
                </Button>
              </div>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Upload a clear photo of the printed letter with the client&apos;s signature. AI only
                checks that a signature is present on the document.
              </p>
              <label className="form-field">
                <span className="form-field__label">Signed letter image</span>
                <input
                  ref={verifyInputRef}
                  className="form-field__input"
                  type="file"
                  accept={IMAGE_ACCEPT}
                  onChange={(e) => onPickVerifyFile(e.target.files?.[0] ?? null)}
                />
              </label>
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
                  {busyId === verifyFor.id ? "Verifying…" : "Verify signature"}
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
