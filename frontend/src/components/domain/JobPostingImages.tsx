import { useEffect, useRef, useState } from "react";
import { downloadJobImage } from "../../api/jobDescriptions";
import { Button } from "../ui/Button";
import { FilePreviewModal, type FilePreviewRequest } from "./FilePreviewModal";

const MAX_JOB_IMAGES = 8;

export function JobPostingImageGallery({
  jobId,
  count,
  onRemove,
}: {
  jobId: number;
  count: number;
  onRemove?: (index: number) => void;
}) {
  const [urls, setUrls] = useState<(string | null)[]>([]);
  const urlsRef = useRef<string[]>([]);
  const [preview, setPreview] = useState<FilePreviewRequest | null>(null);

  useEffect(() => {
    let cancelled = false;
    urlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    urlsRef.current = [];
    setUrls([]);
    if (!jobId || count <= 0) return;

    async function load() {
      const created: string[] = [];
      const next: (string | null)[] = [];
      for (let index = 0; index < count; index += 1) {
        try {
          const blob = await downloadJobImage(jobId, index);
          const url = URL.createObjectURL(blob);
          created.push(url);
          next.push(url);
        } catch {
          next.push(null);
        }
      }
      if (cancelled) {
        created.forEach((url) => URL.revokeObjectURL(url));
        return;
      }
      urlsRef.current = created;
      setUrls(next);
    }

    void load();
    return () => {
      cancelled = true;
      urlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      urlsRef.current = [];
    };
  }, [jobId, count]);

  if (count <= 0) return null;

  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
          gap: "var(--space-3)",
        }}
      >
        {Array.from({ length: count }, (_, index) => (
          <figure
            key={`${jobId}-${index}`}
            style={{
              margin: 0,
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              overflow: "hidden",
              background: "var(--color-surface-alt)",
            }}
          >
            {urls[index] ? (
              <button
                type="button"
                onClick={() =>
                  setPreview({
                    key: `job-${jobId}-image-${index}`,
                    title: `Job posting image ${index + 1}`,
                    filename: `job-${jobId}-image-${index + 1}.jpg`,
                    load: () => downloadJobImage(jobId, index),
                  })
                }
                style={{
                  display: "block",
                  width: "100%",
                  padding: 0,
                  border: 0,
                  background: "transparent",
                  cursor: "zoom-in",
                }}
                aria-label={`View job posting image ${index + 1}`}
              >
                <img
                  src={urls[index] ?? ""}
                  alt={`Job posting ${index + 1}`}
                  style={{ width: "100%", height: 120, objectFit: "cover", display: "block" }}
                />
              </button>
            ) : (
              <div
                style={{
                  height: 120,
                  display: "grid",
                  placeItems: "center",
                  color: "var(--color-text-muted)",
                  fontSize: "var(--text-sm)",
                }}
              >
                Loading…
              </div>
            )}
            {onRemove ? (
              <div style={{ padding: "var(--space-2)" }}>
                <Button type="button" variant="destructive" onClick={() => onRemove(index)}>
                  Remove
                </Button>
              </div>
            ) : null}
          </figure>
        ))}
      </div>
      {preview ? <FilePreviewModal preview={preview} onClose={() => setPreview(null)} /> : null}
    </>
  );
}

export { MAX_JOB_IMAGES };
