import type { SheetDraft } from "./salarySheet";

const DRAFT_PREFIX = "hr_salary_sheet_draft:";
const DRAFT_VERSION = 1;
/** Drop abandoned local drafts after two weeks. */
const MAX_AGE_MS = 14 * 24 * 60 * 60 * 1000;

export type SalarySheetDraftPayload = {
  version: typeof DRAFT_VERSION;
  savedAt: string;
  periodMonth: number;
  periodYear: number;
  drafts: Record<string, SheetDraft>;
  removedIds: number[];
};

export function salarySheetDraftKey(periodMonth: number, periodYear: number): string {
  return `${DRAFT_PREFIX}${periodYear}-${String(periodMonth).padStart(2, "0")}`;
}

export function loadSalarySheetDraft(
  periodMonth: number,
  periodYear: number,
): SalarySheetDraftPayload | null {
  try {
    const raw = localStorage.getItem(salarySheetDraftKey(periodMonth, periodYear));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SalarySheetDraftPayload;
    if (parsed.version !== DRAFT_VERSION || !parsed.drafts) return null;
    if (parsed.periodMonth !== periodMonth || parsed.periodYear !== periodYear) return null;
    const age = Date.now() - new Date(parsed.savedAt).getTime();
    if (!Number.isFinite(age) || age > MAX_AGE_MS) {
      clearSalarySheetDraft(periodMonth, periodYear);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveSalarySheetDraft(
  periodMonth: number,
  periodYear: number,
  payload: { drafts: Record<number, SheetDraft>; removedIds: number[] },
): void {
  try {
    const drafts: Record<string, SheetDraft> = {};
    for (const [id, draft] of Object.entries(payload.drafts)) {
      drafts[id] = draft;
    }
    const data: SalarySheetDraftPayload = {
      version: DRAFT_VERSION,
      savedAt: new Date().toISOString(),
      periodMonth,
      periodYear,
      drafts,
      removedIds: payload.removedIds,
    };
    localStorage.setItem(salarySheetDraftKey(periodMonth, periodYear), JSON.stringify(data));
  } catch {
    // Quota / private mode — ignore
  }
}

export function clearSalarySheetDraft(periodMonth: number, periodYear: number): void {
  try {
    localStorage.removeItem(salarySheetDraftKey(periodMonth, periodYear));
  } catch {
    // ignore
  }
}

export function salarySheetDraftHasEdits(payload: SalarySheetDraftPayload | null): boolean {
  if (!payload) return false;
  return Object.keys(payload.drafts).length > 0 || payload.removedIds.length > 0;
}
