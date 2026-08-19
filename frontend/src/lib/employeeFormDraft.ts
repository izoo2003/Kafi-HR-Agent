const DRAFT_PREFIX = "hr_employee_form_draft:";
const DRAFT_VERSION = 1;

export type StoredReferralDraft = {
  fullName: string;
  cnic: string;
  relation: string;
  phone: string;
};

export type EmployeeFormDraftPayload = {
  version: typeof DRAFT_VERSION;
  savedAt: string;
  form: Record<string, string>;
  refForm: StoredReferralDraft;
  pendingReferrals: StoredReferralDraft[];
};

export function employeeFormDraftKey(employeeId: number | "new"): string {
  return `${DRAFT_PREFIX}${employeeId}`;
}

export function loadEmployeeFormDraft(
  employeeId: number | "new",
): EmployeeFormDraftPayload | null {
  try {
    const raw = localStorage.getItem(employeeFormDraftKey(employeeId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as EmployeeFormDraftPayload;
    if (parsed.version !== DRAFT_VERSION || !parsed.form) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveEmployeeFormDraft(
  employeeId: number | "new",
  payload: Omit<EmployeeFormDraftPayload, "version" | "savedAt">,
): void {
  try {
    const data: EmployeeFormDraftPayload = {
      version: DRAFT_VERSION,
      savedAt: new Date().toISOString(),
      ...payload,
    };
    localStorage.setItem(employeeFormDraftKey(employeeId), JSON.stringify(data));
  } catch {
    // Quota or private mode — ignore
  }
}

export function clearEmployeeFormDraft(employeeId: number | "new"): void {
  localStorage.removeItem(employeeFormDraftKey(employeeId));
}

export function hasMeaningfulEmployeeDraft(
  form: Record<string, string>,
  refForm: StoredReferralDraft,
  pendingReferrals: StoredReferralDraft[],
  emptyForm: Record<string, string>,
): boolean {
  if (pendingReferrals.length > 0) return true;
  if (refForm.fullName.trim() || refForm.cnic.trim() || refForm.relation.trim() || refForm.phone.trim()) {
    return true;
  }
  return JSON.stringify(form) !== JSON.stringify(emptyForm);
}
