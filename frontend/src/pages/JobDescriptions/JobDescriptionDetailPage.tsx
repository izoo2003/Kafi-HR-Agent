import { Link, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { LinkedInPostResults } from "../../components/domain/LinkedInPostResults";
import { JobPostingImageGallery } from "../../components/domain/JobPostingImages";
import { useAuth } from "../../hooks/useAuth";
import { useCriteria, useDeleteJobDescription, useJobDescription } from "../../hooks/useJobDescriptions";
import { ApiError } from "../../api/client";
import { useState } from "react";

export function JobDescriptionDetailPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("job_descriptions", "write");
  const job = useJobDescription(jobId);
  const criteria = useCriteria(jobId);
  const deleteJob = useDeleteJobDescription();
  const [error, setError] = useState<string | null>(null);

  async function onDelete() {
    if (!job.data) return;
    const applicants = job.data.applicantsCount ?? 0;
    const applicantNote =
      applicants > 0 ? ` This will also remove ${applicants} candidate(s) and their CVs.` : "";
    if (
      !window.confirm(
        `Delete job posting "${job.data.title}"? This cannot be undone.${applicantNote}`,
      )
    ) {
      return;
    }
    setError(null);
    try {
      await deleteJob.mutateAsync(jobId);
      navigate("/job-descriptions", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete job posting");
    }
  }

  if (job.isLoading) {
    return (
      <div className="page">
        <Spinner />
      </div>
    );
  }
  if (!job.data) {
    return <div className="page">Job not found.</div>;
  }

  const applicationFormUrl = job.data.applicationFormUrl;

  // Description may include a generated "How to apply" block with a raw URL.
  // We show the Google Form URL via the dedicated clickable link below,
  // so strip that block here to avoid a non-clickable "link-looking" text.
  function stripHowToApplyCta(text: string) {
    // If we don't have the dedicated applicationFormUrl, keep the CTA block
    // as a fallback (at least the text will still show the URL).
    if (!applicationFormUrl) return text;
    return (text || "").replace(/\n\nHow to apply\s*[\s\S]*$/i, "").trimEnd();
  }

  return (
    <>
      <PageHeader
        title={job.data.title}
        breadcrumb="Job Postings / Detail"
        actions={
          <>
            <Link to={`/job-descriptions/${jobId}/candidates`}>
              <Button variant="primary">Candidates</Button>
            </Link>
            <Link to={`/job-descriptions/${jobId}/edit`}>
              <Button variant="secondary">Edit</Button>
            </Link>
            {canWrite ? (
              <Button
                type="button"
                variant="secondary"
                disabled={deleteJob.isPending}
                onClick={() => void onDelete()}
                style={{ color: "var(--color-status-critical)" }}
              >
                {deleteJob.isPending ? "Deleting…" : "Delete Posting"}
              </Button>
            ) : null}
          </>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-4)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{error}</p> : null}
        <Card status={job.data.status === "open" ? "positive" : "neutral"}>
          <div
            style={{
              display: "flex",
              gap: "var(--space-3)",
              flexWrap: "wrap",
              alignItems: "center",
              marginBottom: "var(--space-3)",
            }}
          >
            <StatusBadge status={job.data.status === "open" ? "approved" : "draft"}>
              {job.data.status}
            </StatusBadge>
            <span style={{ fontFamily: "var(--font-data)", fontSize: "var(--text-sm)" }}>
              Applicants: {job.data.applicantsCount ?? 0}
            </span>
          </div>
          <p style={{ whiteSpace: "pre-wrap" }}>{stripHowToApplyCta(job.data.descriptionText)}</p>
          {(job.data.imagePaths ?? []).length > 0 ? (
            <>
              <h3>Images</h3>
              <JobPostingImageGallery jobId={jobId} count={job.data.imagePaths.length} />
            </>
          ) : null}
          {job.data.requirementsText ? (
            <>
              <h3>Requirements</h3>
              <p style={{ whiteSpace: "pre-wrap" }}>{job.data.requirementsText}</p>
            </>
          ) : null}
          {job.data.applicationFormUrl ? (
            <>
              <h3>Apply via Google Form</h3>
              <p style={{ wordBreak: "break-all" }}>
                <a
                  href={job.data.applicationFormUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: "var(--color-accent)" }}
                >
                  {job.data.applicationFormUrl}
                </a>
              </p>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                Candidates submit their details and CV through this form.
              </p>
            </>
          ) : null}
          {(job.data.linkedinPosts ?? []).length > 0 ? (
            <>
              <h3>LinkedIn</h3>
              <LinkedInPostResults posts={job.data.linkedinPosts ?? []} />
            </>
          ) : null}
        </Card>
        <Card>
          <h3 style={{ marginTop: 0 }}>Skills</h3>
          <p style={{ marginTop: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
            Required level: 1 = very low · 10 = expert
          </p>
          <ul>
            {(criteria.data ?? []).map((c) => {
              const level = c.weight > 1 ? Math.round(c.weight) : Math.round(c.weight * 10);
              return (
                <li key={c.id}>
                  {c.criterionName} — level <span className="font-data">{level}/10</span>
                </li>
              );
            })}
          </ul>
          <Link to={`/job-descriptions/${jobId}/ranking`}>Open ranking →</Link>
        </Card>
      </div>
    </>
  );
}
