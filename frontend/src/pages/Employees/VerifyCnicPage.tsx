import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { verifyCnic } from "../../api/employees";
import { ApiError } from "../../api/client";
import type { CnicVerificationResult } from "../../types/cnic";

const IMAGE_ACCEPT =
  "image/png,image/jpeg,image/webp,image/gif,image/heic,image/heif,.png,.jpg,.jpeg,.webp,.gif,.heic,.heif";

function statusColor(status: string): string {
  if (status === "verified") return "var(--color-status-positive)";
  if (status === "needs_image") return "var(--color-status-info)";
  return "var(--color-status-critical)";
}

function isImageFile(file: File): boolean {
  if (file.type.startsWith("image/")) return true;
  return /\.(png|jpe?g|webp|gif|heic|heif)$/i.test(file.name);
}

export function VerifyCnicPage() {
  const [typedCnic, setTypedCnic] = useState("");
  const [uploadSide, setUploadSide] = useState<"front" | "back">("front");
  const [frontImage, setFrontImage] = useState<File | null>(null);
  const [backImage, setBackImage] = useState<File | null>(null);
  const [frontPreview, setFrontPreview] = useState<string | null>(null);
  const [backPreview, setBackPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CnicVerificationResult | null>(null);

  function assignImage(side: "front" | "back", file: File | null) {
    setResult(null);
    setError(null);
    if (file && !isImageFile(file)) {
      setError("Only images are allowed (PNG, JPG, WEBP, GIF, HEIC) — PDF is not accepted.");
      return;
    }
    if (side === "front") {
      if (frontPreview) URL.revokeObjectURL(frontPreview);
      setFrontImage(file);
      setFrontPreview(file ? URL.createObjectURL(file) : null);
    } else {
      if (backPreview) URL.revokeObjectURL(backPreview);
      setBackImage(file);
      setBackPreview(file ? URL.createObjectURL(file) : null);
    }
  }

  async function onVerify(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!typedCnic.trim()) {
      setError("Type the CNIC number as printed on the card.");
      return;
    }
    if (!frontImage && !backImage) {
      setError("Upload at least the front CNIC image (back is optional but recommended).");
      return;
    }
    if (!frontImage) {
      setError("Front CNIC image is required for verification.");
      return;
    }
    setLoading(true);
    try {
      const res = await verifyCnic(typedCnic.trim(), { front: frontImage, back: backImage });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "CNIC verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Verify my CNIC"
        breadcrumb="Organization / Employees / Verify CNIC"
        actions={
          <Link to="/employees">
            <Button variant="secondary">Back to employees</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)", maxWidth: 820 }}>
        <Card>
          <div style={{ display: "grid", gap: "var(--space-3)" }}>
            <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>How this works</h2>
            <ol style={{ margin: 0, paddingLeft: "1.2rem", color: "var(--color-text-secondary)" }}>
              <li>Type the 13-digit CNIC (dashes allowed), e.g. 35202-1234567-1.</li>
              <li>
                Use the CNIC side dropdown (Front / Back), then upload that side as an image — PDF is
                not accepted.
              </li>
              <li>Front is required for a match; back is optional. We OCR the front and compare.</li>
            </ol>
            <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-status-warning)" }}>
              This is a document consistency check — not a NADRA government database lookup.
            </p>
          </div>
        </Card>

        <Card>
          <form onSubmit={onVerify} style={{ display: "grid", gap: "var(--space-4)" }}>
            <FormField
              label="CNIC number"
              value={typedCnic}
              onChange={(e) => setTypedCnic(e.target.value)}
              placeholder="35202-1234567-1"
              required
              hint="Enter exactly as on the card (13 digits)."
            />

            <label className="form-field">
              <span className="form-field__label">CNIC side</span>
              <select
                className="form-field__input"
                value={uploadSide}
                onChange={(e) => setUploadSide(e.target.value as "front" | "back")}
              >
                <option value="front">Front of CNIC</option>
                <option value="back">Back of CNIC</option>
              </select>
              <span className="form-field__hint">
                Pick front or back, then choose an image for that side (PDF not allowed).
              </span>
            </label>

            <label className="form-field">
              <span className="form-field__label">
                {uploadSide === "front" ? "Front of CNIC image" : "Back of CNIC image"}
              </span>
              <input
                className="form-field__input"
                type="file"
                accept={IMAGE_ACCEPT}
                onChange={(e) => assignImage(uploadSide, e.target.files?.[0] ?? null)}
              />
              <span className="form-field__hint">Images only: PNG, JPG, WEBP, GIF, HEIC</span>
            </label>

            <div
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))",
              }}
            >
              <div>
                <div style={{ fontSize: "var(--text-xs)", fontWeight: 600, marginBottom: 6 }}>
                  Front {frontImage ? `· ${frontImage.name}` : "· not set"}
                </div>
                {frontPreview ? (
                  <img
                    src={frontPreview}
                    alt="CNIC front preview"
                    style={{
                      maxWidth: "100%",
                      maxHeight: 180,
                      objectFit: "contain",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  />
                ) : (
                  <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                    No front image yet
                  </p>
                )}
              </div>
              <div>
                <div style={{ fontSize: "var(--text-xs)", fontWeight: 600, marginBottom: 6 }}>
                  Back {backImage ? `· ${backImage.name}` : "· not set"}
                </div>
                {backPreview ? (
                  <img
                    src={backPreview}
                    alt="CNIC back preview"
                    style={{
                      maxWidth: "100%",
                      maxHeight: 180,
                      objectFit: "contain",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  />
                ) : (
                  <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                    No back image yet
                  </p>
                )}
              </div>
            </div>

            {error ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{error}</p> : null}
            <div>
              <Button type="submit" variant="primary" disabled={loading}>
                {loading ? "Verifying…" : "Verify CNIC"}
              </Button>
            </div>
          </form>
        </Card>

        {loading ? <Spinner label="Reading CNIC image" /> : null}

        {result ? (
          <Card>
            <div style={{ display: "grid", gap: "var(--space-3)" }}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Result</h2>
              <p style={{ margin: 0, color: statusColor(result.status), fontWeight: 600 }}>
                {result.authentic ? "Verified (image matches typed CNIC)" : "Not verified"}
                {" · "}
                {result.status.replace(/_/g, " ")}
              </p>
              <p style={{ margin: 0 }}>{result.message}</p>
              <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
                Typed: <span className="num">{result.typedCnic}</span>
              </p>
              <div
                style={{
                  display: "grid",
                  gap: 4,
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-secondary)",
                }}
              >
                <div>Format valid: {result.checks.formatValid ? "Yes" : "No"}</div>
                <div>Image provided: {result.checks.imageProvided ? "Yes" : "No"}</div>
                <div>Image readable: {result.checks.imageReadable ? "Yes" : "No"}</div>
                <div>Looks like Pakistan CNIC: {result.checks.looksLikePakistanCnic ? "Yes" : "No"}</div>
                <div>Typed matches image: {result.checks.cnicMatch ? "Yes" : "No"}</div>
              </div>

              {result.extracted && result.authentic ? (
                <div
                  style={{
                    marginTop: "var(--space-2)",
                    padding: "var(--space-4)",
                    background: "var(--color-status-positive-bg)",
                    borderRadius: "var(--radius-md)",
                    display: "grid",
                    gap: "var(--space-2)",
                  }}
                >
                  <strong>Details from CNIC image</strong>
                  <div>
                    CNIC: <span className="num">{result.extracted.cnic ?? "—"}</span>
                  </div>
                  <div>Name: {result.extracted.fullName ?? "—"}</div>
                  <div>Father / Husband: {result.extracted.fatherName ?? "—"}</div>
                  <div>
                    Date of birth: <span className="num">{result.extracted.dateOfBirth ?? "—"}</span>
                  </div>
                  <div>Gender: {result.extracted.gender ?? "—"}</div>
                  <div>
                    Issue date: <span className="num">{result.extracted.issueDate ?? "—"}</span>
                  </div>
                  <div>
                    Expiry date: <span className="num">{result.extracted.expiryDate ?? "—"}</span>
                  </div>
                  <div>Address: {result.extracted.address ?? "—"}</div>
                  {result.extracted.notes ? <div>Notes: {result.extracted.notes}</div> : null}
                </div>
              ) : null}

              <p style={{ margin: 0, fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                {result.disclaimer}
              </p>
            </div>
          </Card>
        ) : null}
      </div>
    </>
  );
}
