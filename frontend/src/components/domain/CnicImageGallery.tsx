import { useEffect, useMemo, useRef, useState } from "react";
import { downloadEmployeeDocument } from "../../api/employees";
import type { EmployeeDocument } from "../../types/employees";
import { Button } from "../ui/Button";

const SIDE_LABELS: Record<string, string> = {
  cnic_front: "CNIC front",
  cnic_back: "CNIC back",
  cnic: "CNIC",
};

type Lightbox = { label: string; url: string };

type Slot = {
  key: string;
  label: string;
  filename: string;
  url: string | null;
  loading: boolean;
  failed: boolean;
  document?: EmployeeDocument;
  pending: boolean;
};

function latestOf(docs: EmployeeDocument[], category: string): EmployeeDocument | undefined {
  return docs
    .filter((d) => String(d.category) === category)
    .sort((a, b) => b.id - a.id)[0];
}

function useFilePreviewUrl(file: File | null): string | null {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const next = URL.createObjectURL(file);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);
  return url;
}

export function CnicImageGallery({
  employeeId,
  documents,
  pendingFront,
  pendingBack,
  canRemove,
  onRemove,
  onDownload,
  onError,
}: {
  employeeId: number | null;
  documents: EmployeeDocument[];
  pendingFront?: File | null;
  pendingBack?: File | null;
  canRemove?: boolean;
  onRemove?: (doc: EmployeeDocument) => void;
  onDownload?: (doc: EmployeeDocument) => void;
  onError?: (message: string) => void;
}) {
  const pendingFrontUrl = useFilePreviewUrl(pendingFront ?? null);
  const pendingBackUrl = useFilePreviewUrl(pendingBack ?? null);
  const [urls, setUrls] = useState<Record<number, string>>({});
  const [failedIds, setFailedIds] = useState<Set<number>>(() => new Set());
  const [brokenUrls, setBrokenUrls] = useState<Set<string>>(() => new Set());
  const [loading, setLoading] = useState(false);
  const [lightbox, setLightbox] = useState<Lightbox | null>(null);
  const urlsRef = useRef<string[]>([]);
  const documentsRef = useRef(documents);
  documentsRef.current = documents;

  const docIds = documents.map((d) => d.id).join(",");

  useEffect(() => {
    let cancelled = false;
    urlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    urlsRef.current = [];
    setUrls({});
    setFailedIds(new Set());
    setBrokenUrls(new Set());
    const currentDocs = documentsRef.current;
    if (employeeId == null || currentDocs.length === 0) {
      setLoading(false);
      return;
    }
    const id = employeeId;

    async function load() {
      setLoading(true);
      const created: string[] = [];
      const next: Record<number, string> = {};
      const failed = new Set<number>();
      for (const doc of currentDocs) {
        try {
          const blob = await downloadEmployeeDocument(id, doc.id);
          const url = URL.createObjectURL(blob);
          created.push(url);
          next[doc.id] = url;
        } catch {
          failed.add(doc.id);
        }
      }
      if (cancelled) {
        created.forEach((url) => URL.revokeObjectURL(url));
        return;
      }
      urlsRef.current = created;
      setUrls(next);
      setFailedIds(failed);
      setLoading(false);
      if (failed.size > 0) {
        onError?.("Could not load one or more CNIC images.");
      }
    }

    void load();
    return () => {
      cancelled = true;
      urlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      urlsRef.current = [];
    };
  }, [employeeId, docIds, onError]);

  useEffect(() => {
    if (!lightbox) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setLightbox(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox]);

  const slots = useMemo<Slot[]>(() => {
    const frontDoc = latestOf(documents, "cnic_front");
    const backDoc = latestOf(documents, "cnic_back");
    const used = new Set<number>();
    const out: Slot[] = [];

    if (pendingFront) {
      out.push({
        key: "pending-front",
        label: "CNIC front",
        filename: pendingFront.name,
        url: pendingFrontUrl,
        loading: false,
        failed: false,
        pending: true,
      });
    } else if (frontDoc) {
      used.add(frontDoc.id);
      out.push({
        key: `doc-${frontDoc.id}`,
        label: SIDE_LABELS.cnic_front,
        filename: frontDoc.title || frontDoc.originalFilename,
        url: urls[frontDoc.id] ?? null,
        loading: loading && !urls[frontDoc.id] && !failedIds.has(frontDoc.id),
        failed: failedIds.has(frontDoc.id),
        document: frontDoc,
        pending: false,
      });
    }

    if (pendingBack) {
      out.push({
        key: "pending-back",
        label: "CNIC back",
        filename: pendingBack.name,
        url: pendingBackUrl,
        loading: false,
        failed: false,
        pending: true,
      });
    } else if (backDoc) {
      used.add(backDoc.id);
      out.push({
        key: `doc-${backDoc.id}`,
        label: SIDE_LABELS.cnic_back,
        filename: backDoc.title || backDoc.originalFilename,
        url: urls[backDoc.id] ?? null,
        loading: loading && !urls[backDoc.id] && !failedIds.has(backDoc.id),
        failed: failedIds.has(backDoc.id),
        document: backDoc,
        pending: false,
      });
    }

    for (const doc of documents) {
      if (used.has(doc.id)) continue;
      out.push({
        key: `doc-${doc.id}`,
        label: SIDE_LABELS[String(doc.category)] ?? String(doc.category),
        filename: doc.title || doc.originalFilename,
        url: urls[doc.id] ?? null,
        loading: loading && !urls[doc.id] && !failedIds.has(doc.id),
        failed: failedIds.has(doc.id),
        document: doc,
        pending: false,
      });
    }
    return out;
  }, [
    documents,
    failedIds,
    loading,
    pendingBack,
    pendingBackUrl,
    pendingFront,
    pendingFrontUrl,
    urls,
  ]);

  if (slots.length === 0) return null;

  function canView(slot: Slot): boolean {
    return Boolean(slot.url) && !brokenUrls.has(slot.url ?? "");
  }

  function openSlot(slot: Slot) {
    if (slot.url && canView(slot)) {
      setLightbox({ label: slot.label, url: slot.url });
    }
  }

  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: "var(--space-4)",
        }}
      >
        {slots.map((slot) => {
          const previewable = canView(slot);
          return (
            <figure
              key={slot.key}
              style={{
                margin: 0,
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                overflow: "hidden",
                background: "var(--color-surface)",
                display: "grid",
                gridTemplateRows: "auto 1fr auto",
              }}
            >
              <figcaption
                style={{
                  padding: "var(--space-2) var(--space-3)",
                  background: "var(--color-surface-alt)",
                  fontSize: "var(--text-xs)",
                  fontWeight: "var(--weight-semibold)",
                  letterSpacing: "0.02em",
                  textTransform: "uppercase",
                  color: "var(--color-text-secondary)",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "var(--space-2)",
                  alignItems: "center",
                }}
              >
                <span>{slot.label}</span>
                {slot.pending ? (
                  <span style={{ color: "var(--color-status-info)", textTransform: "none" }}>
                    Not saved yet
                  </span>
                ) : null}
              </figcaption>
              <button
                type="button"
                onClick={() => openSlot(slot)}
                disabled={!previewable}
                aria-label={`View ${slot.label}`}
                style={{
                  display: "block",
                  width: "100%",
                  padding: 0,
                  border: 0,
                  background: "var(--color-surface-alt)",
                  cursor: previewable ? "zoom-in" : "default",
                  minHeight: 180,
                }}
              >
                {previewable && slot.url ? (
                  <img
                    src={slot.url}
                    alt={slot.label}
                    onError={() => {
                      const url = slot.url;
                      if (!url) return;
                      setBrokenUrls((prev) => new Set(prev).add(url));
                    }}
                    style={{
                      width: "100%",
                      height: 180,
                      objectFit: "contain",
                      display: "block",
                      background: "var(--color-surface-alt)",
                    }}
                  />
                ) : (
                  <div
                    style={{
                      height: 180,
                      display: "grid",
                      placeItems: "center",
                      color: "var(--color-text-muted)",
                      fontSize: "var(--text-sm)",
                      padding: "var(--space-3)",
                    }}
                  >
                    {slot.loading
                      ? "Loading image…"
                      : slot.failed || Boolean(slot.url && brokenUrls.has(slot.url))
                        ? "Preview unavailable — download to open this file"
                        : "No image"}
                  </div>
                )}
              </button>
              <div
                style={{
                  padding: "var(--space-3)",
                  display: "grid",
                  gap: "var(--space-2)",
                }}
              >
                <span
                  style={{
                    fontSize: "var(--text-xs)",
                    color: "var(--color-text-muted)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={slot.filename}
                >
                  {slot.filename}
                </span>
                <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={!previewable}
                    onClick={() => openSlot(slot)}
                  >
                    View
                  </Button>
                  {slot.document && onDownload ? (
                    <Button type="button" variant="secondary" onClick={() => onDownload(slot.document!)}>
                      Download
                    </Button>
                  ) : null}
                  {slot.document && canRemove && onRemove ? (
                    <Button type="button" variant="destructive" onClick={() => onRemove(slot.document!)}>
                      Remove
                    </Button>
                  ) : null}
                </div>
              </div>
            </figure>
          );
        })}
      </div>

      {lightbox ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cnic-preview-title"
          onClick={() => setLightbox(null)}
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
              width: "min(960px, 100%)",
              maxHeight: "90vh",
              display: "grid",
              gridTemplateRows: "auto 1fr",
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
              <h2 id="cnic-preview-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                {lightbox.label}
              </h2>
              <Button variant="secondary" onClick={() => setLightbox(null)}>
                Close
              </Button>
            </div>
            <div
              style={{
                overflow: "auto",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-surface-alt)",
                padding: "var(--space-3)",
              }}
            >
              <img
                src={lightbox.url}
                alt={lightbox.label}
                style={{ display: "block", maxWidth: "100%", margin: "0 auto" }}
              />
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
