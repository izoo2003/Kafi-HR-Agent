import { useEffect, useMemo, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
} from "../../api/employees";
import { useAuth } from "../../hooks/useAuth";
import {
  useCreateEmployee,
  useCreateEmployeeReference,
  useDeleteEmployeeDocument,
  useDeleteEmployeeReference,
  useDeleteReferenceDocument,
  useDepartments,
  useEmployee,
  useUpdateEmployee,
  useUploadEmployeeDocuments,
  useUploadReferenceDocuments,
} from "../../hooks/useEmployees";
import type {
  EmployeeCreate,
  EmployeeDocumentCategory,
  EmployeeReferenceCreate,
  EmployeeUpdate,
} from "../../types/employees";

type ClientReferralDraft = {
  fullName: string;
  cnic: string;
  relation: string;
  phone: string;
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

const DOC_CATEGORIES: { value: EmployeeDocumentCategory; label: string; hint: string }[] = [
  { value: "cnic", label: "CNIC", hint: "CNIC scan (PDF or images — front/back)" },
  { value: "photo", label: "Photo", hint: "Profile / passport photo" },
  { value: "education", label: "Educational documents", hint: "Degrees, transcripts (multiple OK)" },
  { value: "other", label: "Other", hint: "Contracts, certificates, misc." },
];

function sectionStyle(): CSSProperties {
  return { display: "grid", gap: "var(--space-3)" };
}

function gridStyle(): CSSProperties {
  return {
    display: "grid",
    gap: "var(--space-3)",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
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

export function EmployeeFormPage() {
  const { id } = useParams();
  const isNew = id === undefined || id === "new";
  const employeeId = isNew ? undefined : Number(id);
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");

  const departments = useDepartments();
  const employee = useEmployee(employeeId);
  const createEmp = useCreateEmployee();
  const updateEmp = useUpdateEmployee();

  const uploadDocs = useUploadEmployeeDocuments(employeeId ?? 0);
  const deleteDoc = useDeleteEmployeeDocument(employeeId ?? 0);
  const createRef = useCreateEmployeeReference(employeeId ?? 0);
  const deleteRef = useDeleteEmployeeReference(employeeId ?? 0);
  const uploadRefDocs = useUploadReferenceDocuments(employeeId ?? 0);
  const deleteRefDoc = useDeleteReferenceDocument(employeeId ?? 0);

  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [docCategory, setDocCategory] = useState<EmployeeDocumentCategory>("cnic");
  const [docTitle, setDocTitle] = useState("");
  const [docFiles, setDocFiles] = useState<FileList | null>(null);

  const [refForm, setRefForm] = useState<ClientReferralDraft>({
    fullName: "",
    cnic: "",
    relation: "",
    phone: "",
  });
  /** Drafts collected on Add employee before the profile exists in the API. */
  const [pendingReferrals, setPendingReferrals] = useState<ClientReferralDraft[]>([]);

  useEffect(() => {
    if (!employee.data) return;
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

  const selectedDeptName = useMemo(() => {
    const d = (departments.data ?? []).find((x) => String(x.id) === form.departmentId);
    return d?.name ?? "";
  }, [departments.data, form.departmentId]);

  function patchForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function buildPayload(): EmployeeUpdate {
    return {
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
      setError("Select a role (department) before saving.");
      return;
    }
    try {
      if (isNew) {
        const created = await createEmp.mutateAsync(buildCreatePayload());
        let refsSaved = 0;
        for (const draft of pendingReferrals) {
          const payload: EmployeeReferenceCreate = {
            fullName: draft.fullName.trim(),
            relation: draft.relation.trim(),
            phone: emptyToNull(draft.phone),
            cnic: emptyToNull(draft.cnic),
          };
          await createEmployeeReference(created.id, payload);
          refsSaved += 1;
        }
        setPendingReferrals([]);
        setMessage(
          refsSaved > 0
            ? `Employee created with ${refsSaved} client referral(s). You can add documents next.`
            : "Employee created — you can now add documents and client referrals.",
        );
        navigate(`/employees/${created.id}`, { replace: true });
      } else if (employeeId != null) {
        await updateEmp.mutateAsync({ id: employeeId, payload: buildPayload() });
        setMessage("Employee profile saved");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save employee");
    }
  }

  async function onUploadDocs(e: FormEvent) {
    e.preventDefault();
    if (!employeeId || !docFiles?.length) return;
    setError(null);
    setMessage(null);
    try {
      await uploadDocs.mutateAsync({
        category: docCategory,
        title: docTitle.trim() || undefined,
        files: Array.from(docFiles),
      });
      setDocFiles(null);
      setDocTitle("");
      setMessage("Documents uploaded");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Document upload failed");
    }
  }

  function resetRefForm() {
    setRefForm({ fullName: "", cnic: "", relation: "", phone: "" });
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
      await createRef.mutateAsync({
        fullName: refForm.fullName.trim(),
        relation: refForm.relation.trim(),
        phone: emptyToNull(refForm.phone),
        cnic: emptyToNull(refForm.cnic),
      });
      resetRefForm();
      setMessage("Client referral added");
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
  const refs = employee.data?.references ?? [];
  const readOnly = !canWrite || employee.data?.status === "terminated";

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
                  disabled={!isNew || readOnly}
                  hint={!isNew ? "Code cannot be changed after create" : undefined}
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
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Role</h2>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Assign the employee to a department role. Options come from departments already created.
              </p>
              <div style={gridStyle()}>
                <label className="form-field">
                  <span className="form-field__label">Role (department)</span>
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
                employee, and phone number. You can add more than one before creating the employee.
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

        {!isNew && employeeId != null ? (
          <>
            <Card>
              <div style={sectionStyle()}>
                <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Documents</h2>
                <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  Upload CNIC, educational certificates, photos, and other files (PDF or images). Multiple
                  files allowed per upload.
                </p>

                {canWrite && !readOnly ? (
                  <form onSubmit={onUploadDocs} style={{ display: "grid", gap: "var(--space-3)" }}>
                    <div style={gridStyle()}>
                      <label className="form-field">
                        <span className="form-field__label">Document type</span>
                        <select
                          className="form-field__input"
                          value={docCategory}
                          onChange={(e) =>
                            setDocCategory(e.target.value as EmployeeDocumentCategory)
                          }
                        >
                          {DOC_CATEGORIES.map((c) => (
                            <option key={c.value} value={c.value}>
                              {c.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <FormField
                        label="Title (optional)"
                        value={docTitle}
                        onChange={(e) => setDocTitle(e.target.value)}
                        placeholder="e.g. CNIC front, BSC transcript"
                      />
                      <label className="form-field">
                        <span className="form-field__label">Files (PDF / images)</span>
                        <input
                          className="form-field__input"
                          type="file"
                          accept=".pdf,image/*"
                          multiple
                          onChange={(e) => setDocFiles(e.target.files)}
                        />
                        <span className="form-field__hint">
                          {DOC_CATEGORIES.find((c) => c.value === docCategory)?.hint}
                        </span>
                      </label>
                    </div>
                    <div>
                      <Button type="submit" variant="secondary" disabled={uploadDocs.isPending || !docFiles?.length}>
                        Upload documents
                      </Button>
                    </div>
                  </form>
                ) : null}

                {docs.length === 0 ? (
                  <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                    No documents uploaded yet.
                  </p>
                ) : (
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-2)" }}>
                    {docs.map((d) => (
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
                        <span
                          style={{
                            fontSize: "var(--text-xs)",
                            fontWeight: "var(--weight-medium)",
                            textTransform: "uppercase",
                            color: "var(--color-text-secondary)",
                            minWidth: 88,
                          }}
                        >
                          {d.category}
                        </span>
                        <span style={{ flex: 1 }}>{d.title || d.originalFilename}</span>
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
                  </ul>
                )}
              </div>
            </Card>

            <Card>
              <div style={sectionStyle()}>
                <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Client Referrals</h2>
                <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  Client / personal referrals: reference name, CNIC, relation to employee, and phone
                  number. You can attach supporting PDF or images per referral.
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
                              Remove referral
                            </Button>
                          ) : null}
                        </div>

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
                            Reference documents
                          </div>
                          {(ref.documents ?? []).length === 0 ? (
                            <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
                              No files attached.
                            </p>
                          ) : (
                            <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
                              {ref.documents.map((d) => (
                                <li key={d.id} style={{ marginBottom: 4 }}>
                                  <button
                                    type="button"
                                    style={{
                                      background: "none",
                                      border: "none",
                                      color: "var(--color-accent)",
                                      cursor: "pointer",
                                      padding: 0,
                                      font: "inherit",
                                      textDecoration: "underline",
                                    }}
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
                                    {d.originalFilename}
                                  </button>
                                  {canWrite && !readOnly ? (
                                    <button
                                      type="button"
                                      style={{
                                        marginLeft: 12,
                                        background: "none",
                                        border: "none",
                                        color: "var(--color-status-critical)",
                                        cursor: "pointer",
                                        font: "inherit",
                                        fontSize: "var(--text-sm)",
                                      }}
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
                                    </button>
                                  ) : null}
                                </li>
                              ))}
                            </ul>
                          )}
                          {canWrite && !readOnly ? (
                            <label className="form-field" style={{ marginTop: "var(--space-3)" }}>
                              <span className="form-field__label">Attach PDF / images</span>
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
                                    setMessage(`Files attached for ${ref.fullName}`);
                                  } catch (err) {
                                    setError(
                                      err instanceof ApiError
                                        ? err.message
                                        : "Reference file upload failed",
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
        ) : (
          <Card>
            <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              After creating the employee, you can upload documents on their profile. Client referrals
              can be added above before create, or anytime on the profile.
            </p>
          </Card>
        )}
      </div>
    </>
  );
}
