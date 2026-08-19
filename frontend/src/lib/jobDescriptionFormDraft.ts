import type { ScoringCriteriaInput } from "../types/cvScreening";

const DRAFT_PREFIX = "hr_job_description_form_draft:";
const DRAFT_VERSION = 1;

export type JobDescriptionFormDraftPayload = {
  version: typeof DRAFT_VERSION;
  savedAt: string;
  title: string;
  departmentId: string;
  descriptionText: string;
  requirementsText: string;
  status: "draft" | "open" | "closed";
  skills: ScoringCriteriaInput[];
  selectedLinkedin: string[];
};

export function jobDescriptionFormDraftKey(jobId: number | "new"): string {
  return `${DRAFT_PREFIX}${jobId}`;
}

export function loadJobDescriptionFormDraft(
  jobId: number | "new",
): JobDescriptionFormDraftPayload | null {
  try {
    const raw = localStorage.getItem(jobDescriptionFormDraftKey(jobId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as JobDescriptionFormDraftPayload;
    if (parsed.version !== DRAFT_VERSION) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveJobDescriptionFormDraft(
  jobId: number | "new",
  payload: Omit<JobDescriptionFormDraftPayload, "version" | "savedAt">,
): void {
  try {
    const data: JobDescriptionFormDraftPayload = {
      version: DRAFT_VERSION,
      savedAt: new Date().toISOString(),
      ...payload,
    };
    localStorage.setItem(jobDescriptionFormDraftKey(jobId), JSON.stringify(data));
  } catch {
    // Quota or private mode — ignore
  }
}

export function clearJobDescriptionFormDraft(jobId: number | "new"): void {
  try {
    localStorage.removeItem(jobDescriptionFormDraftKey(jobId));
  } catch {
    // ignore
  }
}

export function hasMeaningfulJobDescriptionDraft(
  draft: Omit<JobDescriptionFormDraftPayload, "version" | "savedAt">,
): boolean {
  if (draft.title.trim()) return true;
  if (draft.departmentId.trim()) return true;
  if (draft.descriptionText.trim()) return true;
  if (draft.requirementsText.trim()) return true;
  if (draft.status !== "draft") return true;
  if (draft.selectedLinkedin.length > 0) return true;
  if (draft.skills.some((s) => (s.criterionName || "").trim().length > 0)) return true;
  return false;
}

