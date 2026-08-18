import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import {
  useJobDescriptions,
  useAssignCandidate,
  useDeleteCandidate,
  useUnassignedCandidates,
} from "../../hooks/useJobDescriptions";
import { usePagination } from "../../hooks/usePagination";
import { ApiError } from "../../api/client";
import { CvPreviewModal } from "../../components/domain/CvPreviewModal";
import { useAuth } from "../../hooks/useAuth";
import type { Candidate } from "../../types/cvScreening";

const SOURCE_LABELS: Record<string, string> = {
  manual: "Manual",
  webmail: "Webmail",
  outlook: "Outlook",
  whatsapp: "WhatsApp",
  gmail: "Gmail",
  google_form: "Google Form",
};

function AssignControl({ candidate }: { candidate: Candidate }) {
  const openJobs = useJobDescriptions({ page: 1, pageSize: 100, status: "open" });
  const assign = useAssignCandidate();
  const [jobId, setJobId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleAssign() {
    if (!jobId) return;
    setError(null);
    try {
      await assign.mutateAsync({ id: candidate.id, jobDescriptionId: Number(jobId) });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Assign failed");
    }
  }

  return (
    <div
      style={{
        display: "grid",
        gap: "var(--space-2)",
        gridTemplateColumns: "minmax(180px, 1fr) auto",
        alignItems: "center",
        width: "100%",
      }}
    >
      <select
        className="form-field__input"
        style={{ minWidth: 0, width: "100%" }}
        value={jobId}
        onChange={(e) => setJobId(e.target.value)}
      >
        <option value="">Select job…</option>
        {(openJobs.data?.items ?? []).map((j) => (
          <option key={j.id} value={j.id}>
            {j.title}
          </option>
        ))}
      </select>
      <Button variant="primary" disabled={!jobId || assign.isPending} onClick={handleAssign}>
        Assign
      </Button>
      {error ? (
        <span
          style={{
            color: "var(--color-status-critical)",
            fontSize: "var(--text-xs)",
            gridColumn: "1 / -1",
          }}
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}

export function UnassignedCandidatesPage() {
  const { page, pageSize, setPage, params } = usePagination();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("cv_screening", "write");
  const unassigned = useUnassignedCandidates(params);
  const remove = useDeleteCandidate();
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Candidate | null>(null);

  async function handleDelete(candidate: Candidate) {
    const label = candidate.fullName?.trim() || `candidate #${candidate.id}`;
    if (!window.confirm(`Remove ${label}? This cannot be undone.`)) return;
    setError(null);
    try {
      await remove.mutateAsync(candidate.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove candidate");
    }
  }

  return (
    <>
      <PageHeader
        title="Unassigned CVs"
        breadcrumb="CV Screening / Unassigned"
        actions={
          <Link to="/cv-screening">
            <Button variant="secondary">Back to CV Screening</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-muted)" }}>
          CVs fetched from HR webmail or the Google Form that could not be confidently
          matched to an open job description. Open the CV, then assign the candidate to a role.
        </p>

        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {unassigned.isLoading ? <Spinner label="Loading unassigned CVs" /> : null}

        {!unassigned.isLoading && (unassigned.data?.total ?? 0) === 0 ? (
          <EmptyState
            title="No unassigned CVs"
            description="Every fetched CV has been matched to a job, or nothing has been synced yet. Use Sync CVs from the CV Screening hub to fetch new submissions."
            actionLabel="Go to CV Screening"
            onAction={() => {
              window.location.href = "/cv-screening";
            }}
          />
        ) : null}

        {unassigned.data && unassigned.data.items.length > 0 ? (
          <>
            <Table headers={["Candidate", "Source", "Submitted", "Best guess", "Actions"]}>
              {unassigned.data.items.map((c) => (
                <tr key={c.id} data-status="warning">
                  <td>
                    <Link to={`/candidates/${c.id}`}>{c.fullName ?? `Candidate #${c.id}`}</Link>
                    <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                      {c.email ?? "—"}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status="info">{SOURCE_LABELS[c.source] ?? c.source}</StatusBadge>
                  </td>
                  <td className="font-data">
                    {c.submittedAt ? new Date(c.submittedAt).toLocaleDateString() : "—"}
                  </td>
                  <td>
                    {c.matchReasoning ? (
                      <span style={{ fontSize: "var(--text-xs)" }}>
                        {c.matchReasoning}
                        {c.matchConfidence != null ? (
                          <span className="font-data"> ({Math.round(c.matchConfidence * 100)}%)</span>
                        ) : null}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <div className="table-actions" style={{ minWidth: 250, alignItems: "start" }}>
                    {canWrite ? <AssignControl candidate={c} /> : null}
                    <Button variant="secondary" onClick={() => setPreview(c)}>
                      View CV
                    </Button>
                    {canWrite ? (
                      <Button
                        variant="destructive"
                        disabled={remove.isPending}
                        onClick={() => handleDelete(c)}
                      >
                        Remove
                      </Button>
                    ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={unassigned.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
      {preview ? (
        <CvPreviewModal
          candidateId={preview.id}
          candidateName={preview.fullName ?? `Candidate #${preview.id}`}
          parsedText={
            typeof preview.parsedData?.raw_text === "string"
              ? preview.parsedData.raw_text
              : typeof preview.parsedData?.rawText === "string"
                ? preview.parsedData.rawText
                : null
          }
          onClose={() => setPreview(null)}
        />
      ) : null}
    </>
  );
}
