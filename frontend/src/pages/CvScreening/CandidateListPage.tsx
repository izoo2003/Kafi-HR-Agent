import { Link, useParams } from "react-router-dom";
import { useRef } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { useCandidates, useJobDescription, useUploadCandidates } from "../../hooks/useJobDescriptions";
import { CANDIDATE_STATUS_LABELS } from "../../constants/statusLabels";
import { ApiError } from "../../api/client";
import { useState } from "react";

export function CandidateListPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const job = useJobDescription(jobId);
  const candidates = useCandidates(jobId);
  const upload = useUploadCandidates(jobId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  async function onFiles(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    try {
      await upload.mutateAsync(Array.from(files));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Candidates"
        breadcrumb={`CV Screening / ${job.data?.title ?? "Job"} / Candidates`}
        actions={
          <>
            <Button variant="secondary" onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
              Upload CV(s)
            </Button>
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
            actionLabel="Upload CV(s)"
            onAction={() => inputRef.current?.click()}
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
                <td>
                  <Link to={`/candidates/${c.id}`}>Detail</Link>
                </td>
              </tr>
            ))}
          </Table>
        ) : null}
      </div>
    </>
  );
}
