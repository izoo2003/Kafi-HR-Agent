import { useEffect, useRef } from "react";
import { clearLocalDraft, saveLocalDraft } from "../lib/localDraft";

type UseLocalDraftPersistOptions<T> = {
  /** Unique key per form instance, e.g. `leave_request_form:12`. */
  scope: string;
  /** True once the user has meaningful unsaved edits. */
  dirty: boolean;
  data: T;
  enabled?: boolean;
  debounceMs?: number;
  /** If true, remove any stored draft instead of writing. */
  isEmpty?: (data: T) => boolean;
  /** Warn when closing the tab with dirty state. */
  warnOnUnload?: boolean;
};

/**
 * Debounced localStorage persistence for in-progress form work.
 * Call `clearLocalDraft(scope)` after a successful server save.
 */
export function useLocalDraftPersist<T>({
  scope,
  dirty,
  data,
  enabled = true,
  debounceMs = 400,
  isEmpty,
  warnOnUnload = true,
}: UseLocalDraftPersistOptions<T>): void {
  const skipFirst = useRef(true);

  useEffect(() => {
    if (!enabled || !scope) return;
    if (!dirty) return;
    if (skipFirst.current) {
      // Avoid writing immediately after a restore hydrate.
      skipFirst.current = false;
    }
    const timer = window.setTimeout(() => {
      if (isEmpty?.(data)) {
        clearLocalDraft(scope);
        return;
      }
      saveLocalDraft(scope, data);
    }, debounceMs);
    return () => window.clearTimeout(timer);
  }, [scope, dirty, data, enabled, debounceMs, isEmpty]);

  useEffect(() => {
    skipFirst.current = true;
  }, [scope]);

  useEffect(() => {
    if (!warnOnUnload || !enabled || !dirty) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [warnOnUnload, enabled, dirty]);
}
