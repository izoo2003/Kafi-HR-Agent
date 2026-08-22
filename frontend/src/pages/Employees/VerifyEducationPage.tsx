import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { verifyEducationDocuments } from "../../api/employees";
import { ApiError } from "../../api/client";
import type { EducationVerificationResult } from "../../types/educationVerification";
import { EDUCATION_VERIFICATION_DISCLAIMER } from "../../constants/educationVerificationDisclaimer";

const DOC_ACCEPT =
  "application/pdf,image/png,image/jpeg,image/webp,image/gif,image/heic,image/heif,.pdf,.png,.jpg,.jpeg,.webp,.gif,.heic,.heif";

function statusColor(status: string): string {
  if (status === "verified") return "var(--color-status-positive)";
  if (status === "partial") return "var(--color-status-warning)";
  if (status === "needs_documents") return "var(--color-status-info)";
  return "var(--color-status-critical)";
}

function institutionTypeLabel(type: string): string {
  return type.replace(/_/g, " ");
}

export function VerifyEducationPage() {
  const [documents, setDocuments] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EducationVerificationResult | null>(null);

  async function onVerify(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (documents.length === 0) {
      setError("Upload at least one education document (PDF or image).");
      return;
    }
    setLoading(true);
    try {
      const res = await verifyEducationDocuments(documents);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Education verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Verify education documents"
        breadcrumb="Organization / Employees Management / Employees Document Verification / Verify education documents"
        actions={
          <Link to="/employees">
            <Button variant="secondary">Back to employees</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)", maxWidth: 900 }}>
        <Card className="education-verification-disclaimer">
          <div
            style={{
              borderLeft: "3px solid var(--color-status-warning)",
              paddingLeft: "var(--space-3)",
              display: "grid",
              gap: "var(--space-2)",
            }}
          >
            <strong style={{ fontSize: "var(--text-sm)", color: "var(--color-status-warning)" }}>
              Important disclaimer
            </strong>
            <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
              {EDUCATION_VERIFICATION_DISCLAIMER}
            </p>
          </div>
        </Card>

        <Card>
          <div style={{ display: "grid", gap: "var(--space-3)" }}>
            <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>How this works</h2>
            <ol style={{ margin: 0, paddingLeft: "1.2rem", color: "var(--color-text-secondary)" }}>
              <li>Upload your education documents — marks sheets, grade sheets, or transcripts (PDF or clear photo).</li>
              <li>AI reads the documents and finds school, college, or university names printed on them.</li>
              <li>
                Each institution is checked to see if it appears to be a real place (using AI knowledge and
                web search when available).
              </li>
            </ol>
            <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-status-warning)" }}>
              See the disclaimer above before submitting documents.
            </p>
          </div>
        </Card>

        <Card>
          <form onSubmit={onVerify} style={{ display: "grid", gap: "var(--space-4)" }}>
            <label className="form-field">
              <span className="form-field__label">Upload your educational documents here</span>
              <input
                className="form-field__input"
                type="file"
                accept={DOC_ACCEPT}
                multiple
                onChange={(e) => {
                  setResult(null);
                  setError(null);
                  setDocuments(Array.from(e.target.files ?? []));
                }}
              />
              <span className="form-field__hint">
                PDF or image — you can select multiple files (marks sheet, grade sheet, transcript, etc.)
              </span>
            </label>

            {documents.length > 0 ? (
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "1.2rem",
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-secondary)",
                }}
              >
                {documents.map((file) => (
                  <li key={`${file.name}-${file.size}-${file.lastModified}`}>{file.name}</li>
                ))}
              </ul>
            ) : null}

            {error ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{error}</p> : null}
            <p
              style={{
                margin: 0,
                fontSize: "var(--text-xs)",
                color: "var(--color-text-muted)",
                lineHeight: 1.5,
              }}
            >
              By clicking Verify, you acknowledge this is an AI-assisted check only — not an official
              registry or board verification.
            </p>
            <div>
              <Button type="submit" variant="primary" disabled={loading}>
                {loading ? "Verifying…" : "Verify education documents"}
              </Button>
            </div>
          </form>
        </Card>

        {loading ? <Spinner label="Reading documents and checking institutions" /> : null}

        {result ? (
          <Card>
            <div style={{ display: "grid", gap: "var(--space-4)" }}>
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Result</h2>
              <p style={{ margin: 0, color: statusColor(result.status), fontWeight: 600 }}>
                {result.verified ? "Verified — institutions appear real" : "Verification incomplete"}
                {" · "}
                {result.status.replace(/_/g, " ")}
              </p>
              <p style={{ margin: 0 }}>{result.message}</p>

              <div
                style={{
                  display: "grid",
                  gap: 4,
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-secondary)",
                }}
              >
                <div>Documents uploaded: {result.checks.documentsProvided}</div>
                <div>Documents readable: {result.checks.documentsReadable ? "Yes" : "No"}</div>
                <div>
                  Look like education documents: {result.checks.looksLikeEducationDocuments ? "Yes" : "No"}
                </div>
              </div>

              {result.documents.length > 0 ? (
                <div style={{ display: "grid", gap: "var(--space-3)" }}>
                  <strong>Documents read</strong>
                  {result.documents.map((doc, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "var(--space-3)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-sm)",
                        display: "grid",
                        gap: 4,
                        fontSize: "var(--text-sm)",
                      }}
                    >
                      <div>
                        Type: {doc.documentType.replace(/_/g, " ")} · Readable:{" "}
                        {doc.readable ? "Yes" : "No"}
                      </div>
                      {doc.studentName ? <div>Student: {doc.studentName}</div> : null}
                      {doc.programOrDegree ? <div>Program: {doc.programOrDegree}</div> : null}
                      {doc.boardOrUniversity ? (
                        <div>Board / university on document: {doc.boardOrUniversity}</div>
                      ) : null}
                      {doc.notes ? <div>Notes: {doc.notes}</div> : null}
                    </div>
                  ))}
                </div>
              ) : null}

              {result.institutions.length > 0 ? (
                <div style={{ display: "grid", gap: "var(--space-3)" }}>
                  <strong>Institution verification</strong>
                  {result.institutions.map((inst) => (
                    <div
                      key={inst.name}
                      style={{
                        padding: "var(--space-4)",
                        borderLeft: `3px solid ${
                          inst.verified
                            ? "var(--color-status-positive)"
                            : "var(--color-status-critical)"
                        }`,
                        background: inst.verified
                          ? "var(--color-status-positive-bg)"
                          : "var(--color-status-critical-bg)",
                        borderRadius: "var(--radius-sm)",
                        display: "grid",
                        gap: "var(--space-2)",
                      }}
                    >
                      <div style={{ fontWeight: 600 }}>
                        {inst.verified ? "Verified" : "Not verified"} · {inst.name}
                      </div>
                      <div style={{ fontSize: "var(--text-sm)" }}>
                        {institutionTypeLabel(inst.institutionType)}
                        {inst.city || inst.country
                          ? ` · ${[inst.city, inst.country].filter(Boolean).join(", ")}`
                          : ""}
                        {" · "}
                        Confidence: {inst.confidence}
                      </div>
                      <div>{inst.verificationNote}</div>
                      {inst.sourceHint ? (
                        <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                          Source: {inst.sourceHint}
                        </div>
                      ) : null}
                    </div>
                  ))}
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
