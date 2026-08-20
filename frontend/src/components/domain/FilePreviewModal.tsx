import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../api/client";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";

function previewKind(blob: Blob, nameHint: string): "pdf" | "image" | "other" {
  const type = (blob.type || "").toLowerCase();
  const lower = nameHint.toLowerCase();
  if (type.includes("pdf") || lower.endsWith(".pdf")) return "pdf";
  if (type.startsWith("image/") || /\.(png|jpe?g|webp|gif|bmp|tiff?|heic|heif)$/.test(lower)) {
    return "image";
  }
  return "other";
}

function blobForPreview(blob: Blob, filename: string): Blob {
  const type = (blob.type || "").toLowerCase();
  if (type && type !== "application/octet-stream") return blob;
  const lower = filename.toLowerCase();
  if (lower.endsWith(".pdf")) return new Blob([blob], { type: "application/pdf" });
  if (lower.endsWith(".png")) return new Blob([blob], { type: "image/png" });
  if (/\.jpe?g$/.test(lower)) return new Blob([blob], { type: "image/jpeg" });
  if (lower.endsWith(".webp")) return new Blob([blob], { type: "image/webp" });
  if (lower.endsWith(".gif")) return new Blob([blob], { type: "image/gif" });
  return blob;
}

export type FilePreviewRequest = {
  key: string;
  title: string;
  filename: string;
  load: () => Promise<Blob>;
};

export function FilePreviewModal({
  preview,
  onClose,
}: {
  preview: FilePreviewRequest;
  onClose: () => void;
}) {
  const { key, title, filename } = preview;
  const loadRef = useRef(preview.load);
  loadRef.current = preview.load;
  const [url, setUrl] = useState<string | null>(null);
  const [kind, setKind] = useState<"pdf" | "image" | "other">("other");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [blob, setBlob] = useState<Blob | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setUrl(null);
    setBlob(null);
    loadRef
      .current()
      .then((raw) => {
        if (cancelled) return;
        const next = blobForPreview(raw, filename);
        setBlob(next);
        const nextKind = previewKind(next, filename);
        setKind(nextKind);
        objectUrl = URL.createObjectURL(next);
        setUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Could not load file");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [key, filename]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function download() {
    if (!blob) return;
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(href);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="file-preview-title"
      onClick={onClose}
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
          gridTemplateRows: "auto 1fr auto",
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
          <h2 id="file-preview-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
            {title}
          </h2>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
        <div
          style={{
            minHeight: 280,
            overflow: "auto",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-surface-alt)",
          }}
        >
          {loading ? (
            <div style={{ padding: "var(--space-6)" }}>
              <Spinner label="Loading file" />
            </div>
          ) : null}
          {error ? (
            <p style={{ color: "var(--color-status-critical)", margin: "var(--space-4)" }}>{error}</p>
          ) : null}
          {!loading && !error && kind === "pdf" && url ? (
            <iframe title={title} src={url} style={{ width: "100%", height: "70vh", border: 0 }} />
          ) : null}
          {!loading && !error && kind === "image" && url ? (
            <img
              src={url}
              alt={title}
              style={{ display: "block", maxWidth: "100%", margin: "0 auto" }}
            />
          ) : null}
          {!loading && !error && kind === "other" ? (
            <p style={{ margin: "var(--space-4)", color: "var(--color-text-secondary)" }}>
              This file type cannot be previewed in the browser. Download it instead.
            </p>
          ) : null}
        </div>
        <div>
          <Button variant="secondary" disabled={!blob} onClick={download}>
            Download
          </Button>
        </div>
      </div>
    </div>
  );
}
