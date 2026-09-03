const DRAFT_PREFIX = "hr_local_draft:";
const DRAFT_VERSION = 1;
const MAX_AGE_MS = 14 * 24 * 60 * 60 * 1000;

export type LocalDraftEnvelope<T> = {
  version: typeof DRAFT_VERSION;
  savedAt: string;
  data: T;
};

export function draftScopeKey(scope: string): string {
  return `${DRAFT_PREFIX}${scope}`;
}

export function loadLocalDraft<T>(scope: string): LocalDraftEnvelope<T> | null {
  try {
    const raw = window.localStorage.getItem(draftScopeKey(scope));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LocalDraftEnvelope<T>;
    if (parsed.version !== DRAFT_VERSION) return null;
    const age = Date.now() - new Date(parsed.savedAt).getTime();
    if (!Number.isFinite(age) || age > MAX_AGE_MS) {
      clearLocalDraft(scope);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveLocalDraft<T>(scope: string, data: T): void {
  try {
    const payload: LocalDraftEnvelope<T> = {
      version: DRAFT_VERSION,
      savedAt: new Date().toISOString(),
      data,
    };
    window.localStorage.setItem(draftScopeKey(scope), JSON.stringify(payload));
  } catch {
    // Ignore quota/private-mode failures.
  }
}

export function clearLocalDraft(scope: string): void {
  try {
    window.localStorage.removeItem(draftScopeKey(scope));
  } catch {
    // ignore
  }
}

export function formatDraftRestoredMessage(
  savedAt: string | null | undefined,
  label = "draft",
): string {
  if (!savedAt) return `Restored unsaved ${label}.`;
  const when = new Date(savedAt);
  if (Number.isNaN(when.getTime())) return `Restored unsaved ${label}.`;
  return `Restored unsaved ${label} from ${when.toLocaleString()}.`;
}
