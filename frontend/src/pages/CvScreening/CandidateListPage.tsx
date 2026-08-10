import { Link, useParams } from "react-router-dom";
import { useRef, useState } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import {
  useCandidates,
  useDeleteCandidate,
  useJobDescription,
  useUploadCandidates,
} from "../../hooks/useJobDescriptions";
import { CANDIDATE_STATUS_LABELS } from "../../constants/statusLabels";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";

export function CandidateListPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("cv_screening", "write");
  const job = useJobDescription(jobId);
  const candidates = useCandidates(jobId);
  const upload = useUploadCandidates(jobId);
  const remove = useDeleteCandidate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function onFiles(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    try {
      await upload.mutateAsync(Array.from(files));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    }
  }

  async function handleDelete(candidateId: number, name: string | null) {
    const label = name?.trim() || `candidate #${candidateId}`;
    if (!window.confirm(`Remove ${label} from this job posting? This cannot be undone.`)) {
      return;
    }
    setError(null);
    setDeletingId(candidateId);
    try {
      await remove.mutateAsync(candidateId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove candidate");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Candidates"
        breadcrumb={`CV Screening / ${job.data?.title ?? "Job"} / Candidates`}
        actions={
          <>
            {canWrite ? (
              <Button variant="secondary" onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
                Upload CV(s)
              </Button>
            ) : null}
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              multiple
              hidden
              onChange={(e) => onFiles(e.target.files)}
            />
            <Link to={`/job-descriptions/${jobId}/ranking`}>
              <Button variant="primary">View Ranking</Button>
            </Link>
          </>
        }
      />
      <div className="page">
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {candidates.isLoading ? <Spinner label="Loading candidates" /> : null}
        {candidates.data && candidates.data.items.length === 0 ? (
          <EmptyState
            title="No candidates yet"
            description="Upload a CV (PDF/DOCX/TXT) to start screening for this role. Parsing and scoring run automatically."
            actionLabel={canWrite ? "Upload CV(s)" : undefined}
            onAction={canWrite ? () => inputRef.current?.click() : undefined}
          />
        ) : null}
        {candidates.data && candidates.data.items.length > 0 ? (
          <Table headers={["Name", "Email", "Status", ""]}>
            {candidates.data.items.map((c) => (
              <tr key={c.id} data-status={c.status}>
                <td>{c.fullName ?? "—"}</td>
                <td>{c.email ?? "—"}</td>
                <td>
                  <StatusBadge status={c.status}>
                    {CANDIDATE_STATUS_LABELS[c.status as keyof typeof CANDIDATE_STATUS_LABELS] ?? c.status}
                  </StatusBadge>
                </td>
                <td style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
                  <Link to={`/candidates/${c.id}`}>Detail</Link>
                  {canWrite ? (
                    <Button
                      variant="destructive"
                      disabled={remove.isPending && deletingId === c.id}
                      onClick={() => handleDelete(c.id, c.fullName)}
                    >
                      {deletingId === c.id ? "Removing…" : "Remove"}
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </Table>
        ) : null}
      </div>
    </>
  );
}
