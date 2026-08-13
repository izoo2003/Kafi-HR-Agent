import { Link, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { useCriteria, useJobDescription } from "../../hooks/useJobDescriptions";

export function JobDescriptionDetailPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const job = useJobDescription(jobId);
  const criteria = useCriteria(jobId);

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
          </>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-4)" }}>
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
          <p style={{ whiteSpace: "pre-wrap" }}>{job.data.descriptionText}</p>
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
