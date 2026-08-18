import { useEffect, useState } from "react";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";
import { downloadCandidateCv } from "../../api/jobDescriptions";
import { ApiError } from "../../api/client";

type Props = {
  candidateId: number;
  candidateName: string;
  parsedText?: string | null;
  onClose: () => void;
};

function previewKind(blob: Blob, nameHint: string): "pdf" | "image" | "text" | "other" {
  const type = (blob.type || "").toLowerCase();
  const lower = nameHint.toLowerCase();
  if (type.includes("pdf") || lower.endsWith(".pdf")) return "pdf";
  if (type.startsWith("image/") || /\.(png|jpe?g|webp|gif|bmp|tiff?|heic|heif)$/.test(lower)) {
    return "image";
  }
  if (type.startsWith("text/") || lower.endsWith(".txt")) return "text";
  return "other";
}

export function CvPreviewModal({ candidateId, candidateName, parsedText, onClose }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [kind, setKind] = useState<"pdf" | "image" | "text" | "other">("other");
  const [text, setText] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setLoading(true);
    setError(null);
    downloadCandidateCv(candidateId)
      .then(async (blob) => {
        if (cancelled) return;
        const nextKind = previewKind(blob, blob.type);
        setKind(nextKind);
        if (nextKind === "text") {
          setText(await blob.text());
        } else {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Could not load CV");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [candidateId]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="cv-preview-title"
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
        <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-3)", alignItems: "center" }}>
          <h2 id="cv-preview-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
            CV — {candidateName}
          </h2>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
        <div
          style={{
            minHeight: 360,
            overflow: "auto",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-surface-alt)",
          }}
        >
          {loading ? (
            <div style={{ padding: "var(--space-6)" }}>
              <Spinner label="Loading CV" />
            </div>
          ) : null}
          {error ? (
            <p style={{ color: "var(--color-status-critical)", padding: "var(--space-4)" }}>{error}</p>
          ) : null}
          {!loading && !error && kind === "pdf" && url ? (
            <iframe title="CV preview" src={url} style={{ width: "100%", height: "70vh", border: 0 }} />
          ) : null}
          {!loading && !error && kind === "image" && url ? (
            <img
              src={url}
              alt={`CV for ${candidateName}`}
              style={{ display: "block", maxWidth: "100%", margin: "0 auto" }}
            />
          ) : null}
          {!loading && !error && kind === "text" ? (
            <pre
              style={{
                margin: 0,
                padding: "var(--space-4)",
                whiteSpace: "pre-wrap",
                fontFamily: "var(--font-data)",
                fontSize: "var(--text-sm)",
              }}
            >
              {text || parsedText || "No text in this CV."}
            </pre>
          ) : null}
          {!loading && !error && kind === "other" ? (
            <div style={{ padding: "var(--space-4)", display: "grid", gap: "var(--space-3)" }}>
              <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                This file type cannot be previewed in the browser (usually Word). Download it, or use
                the extracted text below if parsing already ran.
              </p>
              {url ? (
                <a href={url} download style={{ color: "var(--color-accent)", fontWeight: "var(--weight-medium)" }}>
                  Download CV
                </a>
              ) : null}
              {parsedText ? (
                <pre
                  style={{
                    margin: 0,
                    padding: "var(--space-3)",
                    whiteSpace: "pre-wrap",
                    fontFamily: "var(--font-data)",
                    fontSize: "var(--text-sm)",
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-sm)",
                    maxHeight: "40vh",
                    overflow: "auto",
                  }}
                >
                  {parsedText}
                </pre>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
