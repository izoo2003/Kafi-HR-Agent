import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { CnicImageGallery } from "../../components/domain/CnicImageGallery";
import { FilePreviewModal, type FilePreviewRequest } from "../../components/domain/FilePreviewModal";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { ApiError } from "../../api/client";
import {
  createEmployeeReference,
  downloadEmployeeDocument,
  downloadReferenceDocument,
  uploadEmployeeDocuments,
  uploadReferenceDocuments,
} from "../../api/employees";
import { useAuth } from "../../hooks/useAuth";
import { isSelfService } from "../../lib/selfService";
import {
  useCreateEmployee,
  useCreateEmployeeReference,
  useDeleteEmployeeDocument,
  useDeleteEmployeeReference,
  useDeleteReferenceDocument,
  useDepartments,
  useEmployee,
  useUpdateEmployee,
  useUpdateEmployeeReference,
  useUploadEmployeeDocuments,
  useUploadReferenceDocuments,
} from "../../hooks/useEmployees";
import type {
  EmployeeCreate,
  EmployeeReference,
  EmployeeReferenceCreate,
  EmployeeUpdate,
} from "../../types/employees";
import { EMPLOYEE_LOCATIONS } from "../../types/employees";
import {
  clearEmployeeFormDraft,
  hasMeaningfulEmployeeDraft,
  loadEmployeeFormDraft,
  saveEmployeeFormDraft,
  type StoredReferralDraft,
} from "../../lib/employeeFormDraft";

type ClientReferralDraft = {
  fullName: string;
  cnic: string;
  relation: string;
  phone: string;
  files: File[];
};

type FormState = {
  employeeCode: string;
  fullName: string;
  cnic: string;
  email: string;
  personalMobile: string;
  alternateMobile: string;
  fatherName: string;
  dateOfBirth: string;
  gender: string;
  maritalStatus: string;
  currentAddress: string;
  permanentAddress: string;
  city: string;
  nationality: string;
  location: string;
  departmentId: string;
  employmentType: string;
  dateJoined: string;
  bankName: string;
  accountTitle: string;
  accountNumber: string;
  iban: string;
  branchName: string;
  branchCode: string;
  baseSalary: string;
};

const emptyForm: FormState = {
  employeeCode: "",
  fullName: "",
  cnic: "",
  email: "",
  personalMobile: "",
  alternateMobile: "",
  fatherName: "",
  dateOfBirth: "",
  gender: "",
  maritalStatus: "",
  currentAddress: "",
  permanentAddress: "",
  city: "",
  nationality: "Pakistani",
  location: "",
  departmentId: "",
  employmentType: "full_time",
  dateJoined: "",
  bankName: "",
  accountTitle: "",
  accountNumber: "",
  iban: "",
  branchName: "",
  branchCode: "",
  baseSalary: "",
};

const emptyReferralDraft = (): ClientReferralDraft => ({
  fullName: "",
  cnic: "",
  relation: "",
  phone: "",
  files: [],
});

function sectionStyle(): CSSProperties {
  return { display: "grid", gap: "var(--space-3)" };
}

function gridStyle(): CSSProperties {
  return {
    display: "grid",
    gap: "var(--space-3)",
    gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))",
  };
}

function emptyToNull(v: string): string | null {
  const t = v.trim();
  return t ? t : null;
}

async function openBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function referralToStored(draft: ClientReferralDraft): StoredReferralDraft {
  return {
    fullName: draft.fullName,
    cnic: draft.cnic,
    relation: draft.relation,
    phone: draft.phone,
  };
}

function storedToReferral(stored: StoredReferralDraft): ClientReferralDraft {
  return { ...stored, files: [] };
}

function readDraftBootstrap(isNew: boolean, employeeId: number | undefined) {
  const draftKey: number | "new" = isNew ? "new" : (employeeId ?? "new");
  const draft = loadEmployeeFormDraft(draftKey);
  if (!draft) {
    return {
      draftKey,
      restored: false,
      form: emptyForm,
      refForm: emptyReferralDraft(),
      pendingReferrals: [] as ClientReferralDraft[],
    };
  }
  return {
    draftKey,
    restored: true,
    form: { ...emptyForm, ...draft.form } as FormState,
    refForm: storedToReferral(draft.refForm),
    pendingReferrals: draft.pendingReferrals.map(storedToReferral),
  };
}

export function EmployeeFormPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const viewOnly = searchParams.get("mode") === "view";
  const isNew = id === undefined || id === "new";
  const employeeId = isNew ? undefined : Number(id);
  const navigate = useNavigate();
  const { hasPermission, user } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const selfService = isSelfService(user);

  const draftBootstrap = useMemo(
    () => readDraftBootstrap(isNew, employeeId),
    [isNew, employeeId],
  );
  const draftRestoredRef = useRef(draftBootstrap.restored);
  const skipPersistRef = useRef(true);

  const departments = useDepartments();
  const employee = useEmployee(employeeId);
  const createEmp = useCreateEmployee();
  const updateEmp = useUpdateEmployee();

  const uploadDocs = useUploadEmployeeDocuments(employeeId ?? 0);
  const deleteDoc = useDeleteEmployeeDocument(employeeId ?? 0);
  const createRef = useCreateEmployeeReference(employeeId ?? 0);
  const updateRef = useUpdateEmployeeReference(employeeId ?? 0);
  const deleteRef = useDeleteEmployeeReference(employeeId ?? 0);
  const uploadRefDocs = useUploadReferenceDocuments(employeeId ?? 0);
  const deleteRefDoc = useDeleteReferenceDocument(employeeId ?? 0);

  const [form, setForm] = useState<FormState>(draftBootstrap.form);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(
    draftBootstrap.restored
      ? "Restored unsaved employee details from your last session. Re-attach any files if you had picked them."
      : null,
  );

  const [cnicFrontFile, setCnicFrontFile] = useState<File | null>(null);
  const [cnicBackFile, setCnicBackFile] = useState<File | null>(null);
  const [clientDocTitle, setClientDocTitle] = useState("");
  const [clientDocFiles, setClientDocFiles] = useState<FileList | null>(null);
  const [filePreview, setFilePreview] = useState<FilePreviewRequest | null>(null);

  const [refForm, setRefForm] = useState<ClientReferralDraft>(draftBootstrap.refForm);
  /** Drafts collected on Add employee before the profile exists in the API. */
  const [pendingReferrals, setPendingReferrals] = useState<ClientReferralDraft[]>(
    draftBootstrap.pendingReferrals,
  );
  const [editingRefId, setEditingRefId] = useState<number | null>(null);
  const [editRefForm, setEditRefForm] = useState({
    fullName: "",
    cnic: "",
    relation: "",
    phone: "",
  });

  useEffect(() => {
    if (!employee.data || draftRestoredRef.current) return;
    const e = employee.data;
    setForm({
      employeeCode: e.employeeCode ?? "",
      fullName: e.fullName ?? "",
      cnic: e.cnic ?? "",
      email: e.email ?? "",
      personalMobile: e.personalMobile ?? "",
      alternateMobile: e.alternateMobile ?? "",
      fatherName: e.fatherName ?? "",
      dateOfBirth: e.dateOfBirth ?? "",
      gender: e.gender ?? "",
      maritalStatus: e.maritalStatus ?? "",
      currentAddress: e.currentAddress ?? "",
      permanentAddress: e.permanentAddress ?? "",
      city: e.city ?? "",
      nationality: e.nationality ?? "",
      location: e.location ?? "",
      departmentId: String(e.departmentId ?? ""),
      employmentType: e.employmentType ?? "full_time",
      dateJoined: e.dateJoined ?? "",
      bankName: e.bankName ?? "",
      accountTitle: e.accountTitle ?? "",
      accountNumber: e.accountNumber ?? "",
      iban: e.iban ?? "",
      branchName: e.branchName ?? "",
      branchCode: e.branchCode ?? "",
      baseSalary: e.baseSalary != null ? String(e.baseSalary) : "",
    });
  }, [employee.data]);

  useEffect(() => {
    if (viewOnly || !canWrite) return;
    if (skipPersistRef.current) {
      skipPersistRef.current = false;
      return;
    }
    const storedRef = referralToStored(refForm);
    const storedPending = pendingReferrals.map(referralToStored);
    if (!hasMeaningfulEmployeeDraft(form, storedRef, storedPending, emptyForm)) {
      clearEmployeeFormDraft(draftBootstrap.draftKey);
      return;
    }
    const timer = window.setTimeout(() => {
      saveEmployeeFormDraft(draftBootstrap.draftKey, {
        form,
        refForm: storedRef,
        pendingReferrals: storedPending,
      });
    }, 400);
    return () => window.clearTimeout(timer);
  }, [form, refForm, pendingReferrals, viewOnly, canWrite, draftBootstrap.draftKey]);

  const selectedDeptName = useMemo(() => {
    const d = (departments.data ?? []).find((x) => String(x.id) === form.departmentId);
    return d?.name ?? "";
  }, [departments.data, form.departmentId]);

  function patchForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function buildPayload(): EmployeeUpdate {
    return {
      employeeCode: form.employeeCode.trim(),
      fullName: form.fullName.trim(),
      departmentId: Number(form.departmentId),
      roleTitle: selectedDeptName || undefined,
      employmentType: form.employmentType.trim() || undefined,
      dateJoined: emptyToNull(form.dateJoined),
      baseSalary: form.baseSalary ? Number(form.baseSalary) : null,
      cnic: emptyToNull(form.cnic),
      email: emptyToNull(form.email),
      personalMobile: emptyToNull(form.personalMobile),
      alternateMobile: emptyToNull(form.alternateMobile),
      fatherName: emptyToNull(form.fatherName),
      dateOfBirth: emptyToNull(form.dateOfBirth),
      gender: emptyToNull(form.gender),
      maritalStatus: emptyToNull(form.maritalStatus),
      currentAddress: emptyToNull(form.currentAddress),
      permanentAddress: emptyToNull(form.permanentAddress),
      city: emptyToNull(form.city),
      nationality: emptyToNull(form.nationality),
      location: emptyToNull(form.location),
      bankName: emptyToNull(form.bankName),
      accountTitle: emptyToNull(form.accountTitle),
      accountNumber: emptyToNull(form.accountNumber),
      iban: emptyToNull(form.iban),
      branchName: emptyToNull(form.branchName),
      branchCode: emptyToNull(form.branchCode),
    };
  }

  function buildCreatePayload(): EmployeeCreate {
    const update = buildPayload();
    return {
      ...update,
      employeeCode: form.employeeCode.trim(),
      fullName: form.fullName.trim(),
      departmentId: Number(form.departmentId),
      dateJoined: form.dateJoined.trim() || undefined,
      baseSalary: form.baseSalary ? Number(form.baseSalary) : undefined,
    };
  }

  async function onSaveProfile(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (!form.departmentId) {
      setError("Select a department before saving.");
      return;
    }
    try {
      if (isNew) {
        if (cnicFrontFile || cnicBackFile) {
          const bad = [cnicFrontFile, cnicBackFile].find(
            (file) =>
              file &&
              !file.type.startsWith("image/") &&
              !/\.(png|jpe?g|webp|gif|heic|heif)$/i.test(file.name),
          );
          if (bad) {
            setError(
              "CNIC must be an image file (PNG, JPG, WEBP, GIF, HEIC) — PDF is not allowed.",
            );
            return;
          }
        }
        const created = await createEmp.mutateAsync(buildCreatePayload());
        let refsSaved = 0;
        let filesSaved = 0;
        if (cnicFrontFile) {
          await uploadEmployeeDocuments(created.id, {
            category: "cnic_front",
            title: "CNIC front",
            files: [cnicFrontFile],
          });
          filesSaved += 1;
          setCnicFrontFile(null);
        }
        if (cnicBackFile) {
          await uploadEmployeeDocuments(created.id, {
            category: "cnic_back",
            title: "CNIC back",
            files: [cnicBackFile],
          });
          filesSaved += 1;
          setCnicBackFile(null);
        }
        if (clientDocFiles?.length) {
          await uploadEmployeeDocuments(created.id, {
            category: "client",
            title: clientDocTitle.trim() || "Employee document submission",
            files: Array.from(clientDocFiles),
          });
          filesSaved += clientDocFiles.length;
          setClientDocFiles(null);
          setClientDocTitle("");
        }
        for (const draft of pendingReferrals) {
          const payload: EmployeeReferenceCreate = {
            fullName: draft.fullName.trim(),
            relation: draft.relation.trim(),
            phone: emptyToNull(draft.phone),
            cnic: emptyToNull(draft.cnic),
          };
          const ref = await createEmployeeReference(created.id, payload);
          refsSaved += 1;
          if (draft.files.length > 0) {
            await uploadReferenceDocuments(created.id, ref.id, draft.files);
            filesSaved += draft.files.length;
          }
        }
        setPendingReferrals([]);
        clearEmployeeFormDraft("new");
        setMessage(
          refsSaved > 0
            ? `Employee created with ${refsSaved} client referral(s)${
                filesSaved > 0 ? ` and ${filesSaved} attached file(s)` : ""
              }. You can add more documents next.`
            : "Employee created.",
        );
        navigate(`/employees/${created.id}`, { replace: true });
      } else if (employeeId != null) {
        await updateEmp.mutateAsync({ id: employeeId, payload: buildPayload() });
        clearEmployeeFormDraft(employeeId);
        setMessage("Employee profile saved");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save employee");
    }
  }

  async function onUploadCnicSide(side: "cnic_front" | "cnic_back") {
    if (!employeeId) return;
    const file = side === "cnic_front" ? cnicFrontFile : cnicBackFile;
    if (!file) {
      setError(`Select the ${side === "cnic_front" ? "front" : "back"} CNIC image first.`);
      return;
    }
    if (!file.type.startsWith("image/") && !/\.(png|jpe?g|webp|gif|heic|heif)$/i.test(file.name)) {
      setError("CNIC must be an image file (PNG, JPG, WEBP, GIF, HEIC) — PDF is not allowed.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      await uploadDocs.mutateAsync({
        category: side,
        title: side === "cnic_front" ? "CNIC front" : "CNIC back",
        files: [file],
      });
      if (side === "cnic_front") setCnicFrontFile(null);
      else setCnicBackFile(null);
      setMessage(`${side === "cnic_front" ? "Front" : "Back"} CNIC image uploaded`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "CNIC image upload failed");
    }
  }

  async function onUploadClientDocs(e: FormEvent) {
    e.preventDefault();
    if (!employeeId || !clientDocFiles?.length) return;
    setError(null);
    setMessage(null);
    try {
      await uploadDocs.mutateAsync({
        category: "client",
        title: clientDocTitle.trim() || "Employee document submission",
        files: Array.from(clientDocFiles),
      });
      setClientDocFiles(null);
      setClientDocTitle("");
      setMessage("Employee documents uploaded");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Employee document upload failed");
    }
  }

  function resetRefForm() {
    setRefForm(emptyReferralDraft());
  }

  function onAddReferralDraft(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!refForm.fullName.trim() || !refForm.relation.trim() || !refForm.phone.trim()) {
      setError("Client referral needs reference name, relation, and phone number.");
      return;
    }
    setPendingReferrals((prev) => [
      ...prev,
      {
        fullName: refForm.fullName.trim(),
        cnic: refForm.cnic.trim(),
        relation: refForm.relation.trim(),
        phone: refForm.phone.trim(),
        files: refForm.files,
      },
    ]);
    resetRefForm();
    setMessage("Client referral added — it will be saved when you create the employee.");
  }

  async function onAddReference(e: FormEvent) {
    e.preventDefault();
    if (!employeeId) return;
    setError(null);
    setMessage(null);
    if (!refForm.fullName.trim() || !refForm.relation.trim() || !refForm.phone.trim()) {
      setError("Client referral needs reference name, relation, and phone number.");
      return;
    }
    try {
      const filesToUpload = refForm.files;
      const created = await createRef.mutateAsync({
        fullName: refForm.fullName.trim(),
        relation: refForm.relation.trim(),
        phone: emptyToNull(refForm.phone),
        cnic: emptyToNull(refForm.cnic),
      });
      if (filesToUpload.length > 0) {
        await uploadRefDocs.mutateAsync({
          referenceId: created.id,
          files: filesToUpload,
        });
      }
      resetRefForm();
      setMessage(
        filesToUpload.length > 0
          ? "Client referral added with CNIC / PDF attachments"
          : "Client referral added",
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add client referral");
    }
  }

  if (!isNew && employee.isLoading) {
    return (
      <div className="page">
        <Spinner label="Loading employee" />
      </div>
    );
  }

  if (!isNew && employee.isError) {
    return (
      <div className="page">
        <p style={{ color: "var(--color-status-critical)" }}>Employee not found.</p>
        <Link to="/employees">Back to employees</Link>
      </div>
    );
  }

  const docs = employee.data?.documents ?? [];
  const employeeDocs = docs.filter((d) => d.category !== "client");
  const cnicDocs = employeeDocs.filter((d) =>
    ["cnic_front", "cnic_back", "cnic"].includes(String(d.category)),
  );
  const clientDocs = docs.filter((d) => d.category === "client");
  const refs = employee.data?.references ?? [];
  const readOnly =
    viewOnly || !canWrite || employee.data?.status === "terminated";
  const cnicViewOnly = selfService || viewOnly || !canWrite || employee.data?.status === "terminated";

  function startEditReferral(ref: EmployeeReference) {
    setEditingRefId(ref.id);
    setEditRefForm({
      fullName: ref.fullName,
      cnic: ref.cnic ?? "",
      relation: ref.relation,
      phone: ref.phone ?? "",
    });
  }

  async function onSaveReferralEdit(e: FormEvent) {
    e.preventDefault();
    if (!editingRefId) return;
    setError(null);
    setMessage(null);
    if (!editRefForm.fullName.trim() || !editRefForm.relation.trim() || !editRefForm.phone.trim()) {
      setError("Client referral needs reference name, relation, and phone number.");
      return;
    }
    try {
      await updateRef.mutateAsync({
        referenceId: editingRefId,
        payload: {
          fullName: editRefForm.fullName.trim(),
          relation: editRefForm.relation.trim(),
          phone: emptyToNull(editRefForm.phone),
          cnic: emptyToNull(editRefForm.cnic),
        },
      });
      setEditingRefId(null);
      setMessage("Client referral updated");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update client referral");
    }
  }

  function referralFormFields(onSubmit: (e: FormEvent) => void, submitLabel: string) {
    return (
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "var(--space-3)" }}>
        <div style={gridStyle()}>
          <FormField
            label="Reference name"
            value={refForm.fullName}
            onChange={(e) => setRefForm({ ...refForm, fullName: e.target.value })}
            required
            disabled={readOnly}
          />
          <FormField
            label="CNIC"
            value={refForm.cnic}
            onChange={(e) => setRefForm({ ...refForm, cnic: e.target.value })}
            placeholder="xxxxx-xxxxxxx-x"
            disabled={readOnly}
          />
          <FormField
            label="Relation to employee"
            value={refForm.relation}
            onChange={(e) => setRefForm({ ...refForm, relation: e.target.value })}
            required
            placeholder="e.g. Client, Former manager, Relative"
            disabled={readOnly}
          />
          <FormField
            label="Phone number"
            value={refForm.phone}
            onChange={(e) => setRefForm({ ...refForm, phone: e.target.value })}
            required
            disabled={readOnly}
          />
        </div>
        <label className="form-field">
          <span className="form-field__label">Insert client CNIC image / PDF</span>
          <input
            className="form-field__input"
            type="file"
            accept=".pdf,image/*"
            multiple
            disabled={readOnly}
            onChange={(e) =>
              setRefForm({
                ...refForm,
                files: e.target.files ? Array.from(e.target.files) : [],
              })
            }
          />
          <span className="form-field__hint">
            Attach client CNIC scans or related PDFs with this referral
            {refForm.files.length > 0 ? ` (${refForm.files.length} selected)` : ""}.
          </span>
        </label>
        {refForm.files.length > 0 ? (
          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-2)" }}>
            {refForm.files.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                style={{
                  display: "flex",
                  gap: "var(--space-3)",
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                <span style={{ flex: 1, fontSize: "var(--text-sm)" }}>{file.name}</span>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    setFilePreview({
                      key: `ref-form-${file.name}-${file.size}-${file.lastModified}`,
                      title: file.name,
                      filename: file.name,
                      load: async () => file,
                    })
                  }
                >
                  View
                </Button>
              </li>
            ))}
          </ul>
        ) : null}
        {canWrite && !readOnly ? (
          <div>
            <Button type="submit" variant="secondary" disabled={createRef.isPending}>
              {submitLabel}
            </Button>
          </div>
        ) : null}
      </form>
    );
  }

  return (
    <>
      <PageHeader
        title={isNew ? "Add employee" : form.fullName || "Employee profile"}
        breadcrumb={
          isNew
            ? "Organization / Employees / New"
            : `Organization / Employees / ${form.employeeCode || id}`
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)", maxWidth: 1100 }}>
        <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
          <Link to="/employees">
            <Button type="button" variant="secondary">
              Back to list
            </Button>
          </Link>
          {!isNew && viewOnly && canWrite && employee.data?.status !== "terminated" ? (
            <Link to={`/employees/${employeeId}`}>
              <Button type="button" variant="primary">
                Edit employee
              </Button>
            </Link>
          ) : null}
          {!isNew && !viewOnly && canWrite ? (
            <Link to={`/employees/${employeeId}?mode=view`}>
              <Button type="button" variant="secondary">
                View only
              </Button>
            </Link>
          ) : null}
        </div>

        {error ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)", margin: 0 }}>{message}</p> : null}

        <form
          id="employee-profile-form"
          onSubmit={onSaveProfile}
          style={{ display: "grid", gap: "var(--space-5)" }}
        >
          <Card>
            <div style={sectionStyle()}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Personal details</h2>
              <div style={gridStyle()}>
                <FormField
                  label="Employee code"
                  value={form.employeeCode}
                  onChange={(e) => patchForm("employeeCode", e.target.value)}
                  required
                  disabled={readOnly}
                  hint="Must be unique. Used for attendance import matching."
                />
                <FormField
                  label="Full name"
                  value={form.fullName}
                  onChange={(e) => patchForm("fullName", e.target.value)}
                  required
                  disabled={readOnly}
                />
                <FormField
                  label="Father name"
                  value={form.fatherName}
                  onChange={(e) => patchForm("fatherName", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="CNIC"
                  value={form.cnic}
                  onChange={(e) => patchForm("cnic", e.target.value)}
                  placeholder="xxxxx-xxxxxxx-x"
                  disabled={readOnly}
                />
                <FormField
                  label="Email"
                  type="email"
                  value={form.email}
                  onChange={(e) => patchForm("email", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Personal mobile"
                  value={form.personalMobile}
                  onChange={(e) => patchForm("personalMobile", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Alternate mobile"
                  value={form.alternateMobile}
                  onChange={(e) => patchForm("alternateMobile", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Date of birth"
                  type="date"
                  value={form.dateOfBirth}
                  onChange={(e) => patchForm("dateOfBirth", e.target.value)}
                  disabled={readOnly}
                />
                <label className="form-field">
                  <span className="form-field__label">Gender</span>
                  <select
                    className="form-field__input"
                    value={form.gender}
                    onChange={(e) => patchForm("gender", e.target.value)}
                    disabled={readOnly}
                  >
                    <option value="">Select…</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label className="form-field">
                  <span className="form-field__label">Marital status</span>
                  <select
                    className="form-field__input"
                    value={form.maritalStatus}
                    onChange={(e) => patchForm("maritalStatus", e.target.value)}
                    disabled={readOnly}
                  >
                    <option value="">Select…</option>
                    <option value="single">Single</option>
                    <option value="married">Married</option>
                    <option value="divorced">Divorced</option>
                    <option value="widowed">Widowed</option>
                  </select>
                </label>
                <FormField
                  label="City"
                  value={form.city}
                  onChange={(e) => patchForm("city", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Nationality"
                  value={form.nationality}
                  onChange={(e) => patchForm("nationality", e.target.value)}
                  disabled={readOnly}
                />
              </div>
              <FormField
                label="Current address"
                value={form.currentAddress}
                onChange={(e) => patchForm("currentAddress", e.target.value)}
                disabled={readOnly}
              />
              <FormField
                label="Permanent address"
                value={form.permanentAddress}
                onChange={(e) => patchForm("permanentAddress", e.target.value)}
                disabled={readOnly}
              />
            </div>
          </Card>

          <Card>
            <div style={sectionStyle()}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Department</h2>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Assign the employee to a department. Options come from departments already created.
              </p>
              <div style={gridStyle()}>
                <label className="form-field">
                  <span className="form-field__label">Department</span>
                  <select
                    className="form-field__input"
                    value={form.departmentId}
                    onChange={(e) => patchForm("departmentId", e.target.value)}
                    required
                    disabled={readOnly}
                  >
                    <option value="">Select department…</option>
                    {(departments.data ?? []).map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="form-field">
                  <span className="form-field__label">Employment type</span>
                  <select
                    className="form-field__input"
                    value={form.employmentType}
                    onChange={(e) => patchForm("employmentType", e.target.value)}
                    disabled={readOnly}
                  >
                    <option value="full_time">Full time</option>
                    <option value="part_time">Part time</option>
                    <option value="contract">Contract</option>
                  </select>
                </label>
                <FormField
                  label="Date joined"
                  type="date"
                  value={form.dateJoined}
                  onChange={(e) => patchForm("dateJoined", e.target.value)}
                  disabled={readOnly}
                />
              </div>
            </div>
          </Card>

          <Card>
            <div style={sectionStyle()}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Location</h2>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Workplace site for this employee.
              </p>
              <div style={gridStyle()}>
                <label className="form-field">
                  <span className="form-field__label">Location</span>
                  <select
                    className="form-field__input"
                    value={form.location}
                    onChange={(e) => patchForm("location", e.target.value)}
                    disabled={readOnly}
                  >
                    <option value="">Select location…</option>
                    {EMPLOYEE_LOCATIONS.map((loc) => (
                      <option key={loc} value={loc}>
                        {loc}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          </Card>

          <Card>
            <div style={sectionStyle()}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Bank details</h2>
              <div style={gridStyle()}>
                <FormField
                  label="Bank name"
                  value={form.bankName}
                  onChange={(e) => patchForm("bankName", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Account title"
                  value={form.accountTitle}
                  onChange={(e) => patchForm("accountTitle", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Account number"
                  value={form.accountNumber}
                  onChange={(e) => patchForm("accountNumber", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="IBAN"
                  value={form.iban}
                  onChange={(e) => patchForm("iban", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Branch name"
                  value={form.branchName}
                  onChange={(e) => patchForm("branchName", e.target.value)}
                  disabled={readOnly}
                />
                <FormField
                  label="Branch code"
                  value={form.branchCode}
                  onChange={(e) => patchForm("branchCode", e.target.value)}
                  disabled={readOnly}
                />
              </div>
            </div>
          </Card>

          <Card>
            <div style={sectionStyle()}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Salary details</h2>
              <div style={{ maxWidth: 280 }}>
                <FormField
                  label="Base salary"
                  type="number"
                  min="0"
                  max="9999999999.99"
                  step="0.01"
                  value={form.baseSalary}
                  onChange={(e) => patchForm("baseSalary", e.target.value)}
                  disabled={readOnly}
                  hint="Offered monthly base. Net pay is calculated after attendance deductions and tax."
                />
              </div>
            </div>
          </Card>

        </form>

        {isNew ? (
          <Card>
            <div style={sectionStyle()}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Client Referrals</h2>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Add client / personal referrals for this employee: reference name, CNIC, relation to
                employee, and phone number. Optionally insert CNIC images/PDFs for each referral before
                create.
              </p>
              {referralFormFields(onAddReferralDraft, "Add client referral")}
              {pendingReferrals.length === 0 ? (
                <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                  No client referrals added yet (optional).
                </p>
              ) : (
                <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-2)" }}>
                  {pendingReferrals.map((ref, idx) => (
                    <li
                      key={`${ref.fullName}-${idx}`}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "var(--space-3)",
                        alignItems: "center",
                        flexWrap: "wrap",
                        borderBottom: "1px solid var(--color-border)",
                        paddingBottom: "var(--space-2)",
                      }}
                    >
                      <div>
                        <strong>{ref.fullName}</strong>
                        <div style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                          {ref.relation}
                          {ref.phone ? ` · ${ref.phone}` : ""}
                          {ref.cnic ? ` · CNIC ${ref.cnic}` : ""}
                        </div>
                        {ref.files.length > 0 ? (
                          <ul
                            style={{
                              margin: "var(--space-2) 0 0",
                              padding: 0,
                              listStyle: "none",
                              display: "grid",
                              gap: "var(--space-2)",
                            }}
                          >
                            {ref.files.map((file, fileIdx) => (
                              <li
                                key={`${file.name}-${fileIdx}`}
                                style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}
                              >
                                <span style={{ fontSize: "var(--text-sm)" }}>{file.name}</span>
                                <Button
                                  type="button"
                                  variant="secondary"
                                  onClick={() =>
                                    setFilePreview({
                                      key: `pending-ref-${idx}-${file.name}-${file.size}`,
                                      title: file.name,
                                      filename: file.name,
                                      load: async () => file,
                                    })
                                  }
                                >
                                  View
                                </Button>
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                      <Button
                        type="button"
                        variant="destructive"
                        onClick={() =>
                          setPendingReferrals((prev) => prev.filter((_, i) => i !== idx))
                        }
                      >
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Card>
        ) : null}

        <Card>
          <div style={sectionStyle()}>
            <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>CNIC images</h2>
            <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              {cnicViewOnly
                ? "View or download the front and back of this employee’s CNIC. Uploads are not allowed in this view."
                : isNew
                  ? "Attach front and back CNIC images now. They are saved when you create the employee. Images only (PNG, JPG, WEBP, GIF, HEIC) — PDF is not accepted."
                  : "Upload the front and back of the employee CNIC as images only (PNG, JPG, WEBP, GIF, HEIC). PDF is not accepted here."}
            </p>

            {!cnicViewOnly ? (
              <div style={gridStyle()}>
                <label className="form-field">
                  <span className="form-field__label">Front CNIC image</span>
                  <input
                    className="form-field__input"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif,image/heic,image/heif,.png,.jpg,.jpeg,.webp,.gif,.heic,.heif"
                    onChange={(e) => setCnicFrontFile(e.target.files?.[0] ?? null)}
                  />
                  <span className="form-field__hint">
                    {cnicFrontFile ? cnicFrontFile.name : "Choose front side image"}
                  </span>
                  {!isNew && employeeId != null ? (
                    <div style={{ marginTop: "var(--space-2)" }}>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={uploadDocs.isPending || !cnicFrontFile}
                        onClick={() => onUploadCnicSide("cnic_front")}
                      >
                        Upload front CNIC
                      </Button>
                    </div>
                  ) : null}
                </label>
                <label className="form-field">
                  <span className="form-field__label">Back CNIC image</span>
                  <input
                    className="form-field__input"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif,image/heic,image/heif,.png,.jpg,.jpeg,.webp,.gif,.heic,.heif"
                    onChange={(e) => setCnicBackFile(e.target.files?.[0] ?? null)}
                  />
                  <span className="form-field__hint">
                    {cnicBackFile ? cnicBackFile.name : "Choose back side image"}
                  </span>
                  {!isNew && employeeId != null ? (
                    <div style={{ marginTop: "var(--space-2)" }}>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={uploadDocs.isPending || !cnicBackFile}
                        onClick={() => onUploadCnicSide("cnic_back")}
                      >
                        Upload back CNIC
                      </Button>
                    </div>
                  ) : null}
                </label>
              </div>
            ) : null}

                {cnicDocs.length === 0 && !cnicFrontFile && !cnicBackFile ? (
                  <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                    No CNIC images uploaded yet.
                  </p>
                ) : (
                  <CnicImageGallery
                    employeeId={employeeId ?? null}
                    documents={cnicDocs}
                    pendingFront={cnicFrontFile}
                    pendingBack={cnicBackFile}
                    canRemove={!cnicViewOnly}
                    onError={setError}
                    onDownload={async (doc) => {
                      if (employeeId == null) return;
                      try {
                        const blob = await downloadEmployeeDocument(employeeId, doc.id);
                        await openBlob(blob, doc.originalFilename);
                      } catch {
                        setError("Could not download file");
                      }
                    }}
                    onRemove={async (doc) => {
                      if (!window.confirm(`Remove ${doc.originalFilename}?`)) return;
                      try {
                        await deleteDoc.mutateAsync(doc.id);
                      } catch (err) {
                        setError(err instanceof ApiError ? err.message : "Failed to delete document");
                      }
                    }}
                  />
                )}
              </div>
            </Card>

            <Card>
              <div style={sectionStyle()}>
                <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Employee Document Submission</h2>
                <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  {isNew
                    ? "Attach PDFs or images for this employee’s file. They are saved when you create the employee."
                    : "Upload PDFs or multiple images for this employee’s file. Separate from individual referral attachments below."}
                </p>

                {canWrite && !readOnly ? (
                  <form onSubmit={onUploadClientDocs} style={{ display: "grid", gap: "var(--space-3)" }}>
                    <div style={gridStyle()}>
                      <FormField
                        label="Title (optional)"
                        value={clientDocTitle}
                        onChange={(e) => setClientDocTitle(e.target.value)}
                        placeholder="e.g. Education certificates — March"
                      />
                      <label className="form-field">
                        <span className="form-field__label">PDF / images</span>
                        <input
                          className="form-field__input"
                          type="file"
                          accept=".pdf,image/*"
                          multiple
                          onChange={(e) => setClientDocFiles(e.target.files)}
                        />
                        <span className="form-field__hint">
                          {isNew
                            ? "Select files now; they upload when you create the employee."
                            : "Select one PDF or multiple images in a single upload."}
                        </span>
                      </label>
                    </div>
                    {!isNew && employeeId != null ? (
                      <div>
                        <Button
                          type="submit"
                          variant="secondary"
                          disabled={uploadDocs.isPending || !clientDocFiles?.length}
                        >
                          Upload employee documents
                        </Button>
                      </div>
                    ) : null}
                  </form>
                ) : null}

                {clientDocs.length === 0 && !clientDocFiles?.length ? (
                  <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                    No employee documents submitted yet.
                  </p>
                ) : (
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-2)" }}>
                    {clientDocs.map((d) => (
                      <li
                        key={d.id}
                        style={{
                          display: "flex",
                          gap: "var(--space-3)",
                          alignItems: "center",
                          flexWrap: "wrap",
                          borderBottom: "1px solid var(--color-border)",
                          paddingBottom: "var(--space-2)",
                        }}
                      >
                        <span style={{ flex: 1 }}>{d.title || d.originalFilename}</span>
                        {employeeId != null ? (
                          <>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() =>
                                setFilePreview({
                                  key: `client-${d.id}`,
                                  title: d.title || d.originalFilename,
                                  filename: d.originalFilename,
                                  load: () => downloadEmployeeDocument(employeeId, d.id),
                                })
                              }
                            >
                              View
                            </Button>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={async () => {
                                try {
                                  const blob = await downloadEmployeeDocument(employeeId, d.id);
                                  await openBlob(blob, d.originalFilename);
                                } catch {
                                  setError("Could not download file");
                                }
                              }}
                            >
                              Download
                            </Button>
                          </>
                        ) : null}
                        {canWrite && !readOnly ? (
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={async () => {
                              if (!window.confirm(`Remove ${d.originalFilename}?`)) return;
                              try {
                                await deleteDoc.mutateAsync(d.id);
                              } catch (err) {
                                setError(
                                  err instanceof ApiError ? err.message : "Failed to delete document",
                                );
                              }
                            }}
                          >
                            Remove
                          </Button>
                        ) : null}
                      </li>
                    ))}
                    {clientDocFiles
                      ? Array.from(clientDocFiles).map((file, index) => (
                          <li
                            key={`pending-${file.name}-${index}`}
                            style={{
                              display: "flex",
                              gap: "var(--space-3)",
                              alignItems: "center",
                              flexWrap: "wrap",
                              borderBottom: "1px solid var(--color-border)",
                              paddingBottom: "var(--space-2)",
                            }}
                          >
                            <span style={{ flex: 1 }}>{file.name}</span>
                            <span style={{ color: "var(--color-status-info)", fontSize: "var(--text-xs)" }}>
                              Not saved yet
                            </span>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() =>
                                setFilePreview({
                                  key: `pending-client-${file.name}-${file.size}-${file.lastModified}`,
                                  title: file.name,
                                  filename: file.name,
                                  load: async () => file,
                                })
                              }
                            >
                              View
                            </Button>
                          </li>
                        ))
                      : null}
                  </ul>
                )}
              </div>
            </Card>

        {!isNew && employeeId != null ? (
          <>
            <Card>
              <div style={sectionStyle()}>
                <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Client Referrals</h2>
                <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  Client / personal referrals: reference name, CNIC, relation, and phone. Insert client
                  CNIC image/PDF when adding a referral, or attach files beside any existing referral.
                </p>

                {canWrite && !readOnly
                  ? referralFormFields(onAddReference, "Add client referral")
                  : null}

                {refs.length === 0 ? (
                  <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                    No client referrals added yet.
                  </p>
                ) : (
                  <div style={{ display: "grid", gap: "var(--space-4)" }}>
                    {refs.map((ref) => (
                      <div
                        key={ref.id}
                        style={{
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-md)",
                          padding: "var(--space-4)",
                          display: "grid",
                          gap: "var(--space-3)",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            gap: "var(--space-3)",
                            flexWrap: "wrap",
                          }}
                        >
                          <div>
                            <strong>{ref.fullName}</strong>
                            <div style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                              {ref.relation}
                              {ref.phone ? ` · ${ref.phone}` : ""}
                              {ref.cnic ? ` · CNIC ${ref.cnic}` : ""}
                            </div>
                            {ref.notes ? (
                              <div style={{ fontSize: "var(--text-sm)", marginTop: 4 }}>{ref.notes}</div>
                            ) : null}
                          </div>
                          {canWrite && !readOnly ? (
                            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                              <Button
                                type="button"
                                variant="secondary"
                                onClick={() => startEditReferral(ref)}
                              >
                                Edit
                              </Button>
                              <Button
                                type="button"
                                variant="destructive"
                                onClick={async () => {
                                  if (!window.confirm(`Remove client referral ${ref.fullName}?`)) return;
                                  try {
                                    await deleteRef.mutateAsync(ref.id);
                                  } catch (err) {
                                    setError(
                                      err instanceof ApiError
                                        ? err.message
                                        : "Failed to delete client referral",
                                    );
                                  }
                                }}
                              >
                                Delete
                              </Button>
                            </div>
                          ) : null}
                        </div>

                        {editingRefId === ref.id && canWrite && !readOnly ? (
                          <form
                            onSubmit={onSaveReferralEdit}
                            style={{
                              display: "grid",
                              gap: "var(--space-3)",
                              padding: "var(--space-3)",
                              background: "var(--color-surface-alt)",
                              borderRadius: "var(--radius-md)",
                            }}
                          >
                            <div style={gridStyle()}>
                              <FormField
                                label="Reference name"
                                value={editRefForm.fullName}
                                onChange={(e) =>
                                  setEditRefForm({ ...editRefForm, fullName: e.target.value })
                                }
                                required
                              />
                              <FormField
                                label="CNIC"
                                value={editRefForm.cnic}
                                onChange={(e) =>
                                  setEditRefForm({ ...editRefForm, cnic: e.target.value })
                                }
                              />
                              <FormField
                                label="Relation to employee"
                                value={editRefForm.relation}
                                onChange={(e) =>
                                  setEditRefForm({ ...editRefForm, relation: e.target.value })
                                }
                                required
                              />
                              <FormField
                                label="Phone number"
                                value={editRefForm.phone}
                                onChange={(e) =>
                                  setEditRefForm({ ...editRefForm, phone: e.target.value })
                                }
                                required
                              />
                            </div>
                            <div style={{ display: "flex", gap: "var(--space-2)" }}>
                              <Button type="submit" variant="primary" disabled={updateRef.isPending}>
                                Save referral
                              </Button>
                              <Button
                                type="button"
                                variant="secondary"
                                onClick={() => setEditingRefId(null)}
                              >
                                Cancel
                              </Button>
                            </div>
                          </form>
                        ) : null}

                        <div>
                          <div
                            style={{
                              fontSize: "var(--text-xs)",
                              fontWeight: "var(--weight-semibold)",
                              textTransform: "uppercase",
                              color: "var(--color-text-secondary)",
                              marginBottom: "var(--space-2)",
                            }}
                          >
                            Client CNIC / referral files
                          </div>
                          {(ref.documents ?? []).length === 0 ? (
                            <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
                              No CNIC image or PDF attached yet.
                            </p>
                          ) : (
                            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-2)" }}>
                              {ref.documents.map((d) => (
                                <li
                                  key={d.id}
                                  style={{
                                    display: "flex",
                                    gap: "var(--space-3)",
                                    alignItems: "center",
                                    flexWrap: "wrap",
                                    borderBottom: "1px solid var(--color-border)",
                                    paddingBottom: "var(--space-2)",
                                  }}
                                >
                                  <span style={{ flex: 1 }}>{d.originalFilename}</span>
                                  <Button
                                    type="button"
                                    variant="secondary"
                                    onClick={() =>
                                      setFilePreview({
                                        key: `ref-${ref.id}-doc-${d.id}`,
                                        title: d.originalFilename,
                                        filename: d.originalFilename,
                                        load: () =>
                                          downloadReferenceDocument(employeeId, ref.id, d.id),
                                      })
                                    }
                                  >
                                    View
                                  </Button>
                                  <Button
                                    type="button"
                                    variant="secondary"
                                    onClick={async () => {
                                      try {
                                        const blob = await downloadReferenceDocument(
                                          employeeId,
                                          ref.id,
                                          d.id,
                                        );
                                        await openBlob(blob, d.originalFilename);
                                      } catch {
                                        setError("Could not download file");
                                      }
                                    }}
                                  >
                                    Download
                                  </Button>
                                  {canWrite && !readOnly ? (
                                    <Button
                                      type="button"
                                      variant="destructive"
                                      onClick={async () => {
                                        if (!window.confirm(`Remove ${d.originalFilename}?`)) return;
                                        try {
                                          await deleteRefDoc.mutateAsync({
                                            referenceId: ref.id,
                                            documentId: d.id,
                                          });
                                        } catch (err) {
                                          setError(
                                            err instanceof ApiError
                                              ? err.message
                                              : "Failed to delete file",
                                          );
                                        }
                                      }}
                                    >
                                      Remove
                                    </Button>
                                  ) : null}
                                </li>
                              ))}
                            </ul>
                          )}
                          {canWrite && !readOnly ? (
                            <label className="form-field" style={{ marginTop: "var(--space-3)" }}>
                              <span className="form-field__label">Insert image / PDF (client CNIC)</span>
                              <input
                                className="form-field__input"
                                type="file"
                                accept=".pdf,image/*"
                                multiple
                                onChange={async (e) => {
                                  const files = e.target.files;
                                  if (!files?.length) return;
                                  setError(null);
                                  try {
                                    await uploadRefDocs.mutateAsync({
                                      referenceId: ref.id,
                                      files: Array.from(files),
                                    });
                                    setMessage(`CNIC / PDF attached for ${ref.fullName}`);
                                  } catch (err) {
                                    setError(
                                      err instanceof ApiError
                                        ? err.message
                                        : "Referral file upload failed",
                                    );
                                  }
                                  e.target.value = "";
                                }}
                              />
                            </label>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          </>
        ) : null}

        {canWrite && !readOnly ? (
          <div>
            <Button
              type="submit"
              form="employee-profile-form"
              variant="primary"
              disabled={createEmp.isPending || updateEmp.isPending}
            >
              {isNew ? "Create employee" : "Save profile"}
            </Button>
          </div>
        ) : null}
      </div>
      {filePreview ? (
        <FilePreviewModal preview={filePreview} onClose={() => setFilePreview(null)} />
      ) : null}
    </>
  );
}
