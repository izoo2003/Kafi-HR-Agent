import { Link, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import {
  useAssignCandidate,
  useCandidate,
  useCandidateEvaluation,
  useDeleteCandidate,
  useJobDescriptions,
  usePatchCandidate,
} from "../../hooks/useJobDescriptions";
import { CANDIDATE_STATUS_LABELS } from "../../constants/statusLabels";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import { useState } from "react";
import { CvPreviewModal } from "../../components/domain/CvPreviewModal";

function recommendationStatus(rec: string): string {
  if (rec === "shortlist") return "shortlisted";
  if (rec === "reject") return "rejected";
  return "pending";
}

export function CandidateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const candidateId = Number(id);
  const { hasPermission } = useAuth();
  const canDecide = hasPermission("cv_screening", "write");
  const candidate = useCandidate(candidateId);
  const isAssigned = candidate.data?.jobDescriptionId != null;
  const evaluation = useCandidateEvaluation(candidateId, isAssigned);
  const patch = usePatchCandidate();
  const remove = useDeleteCandidate();
  const assign = useAssignCandidate();
  const openJobs = useJobDescriptions({ page: 1, pageSize: 100, status: "open" });
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [assignJobId, setAssignJobId] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);

  async function setStatus(status: "shortlisted" | "rejected") {
    setError(null);
    setMessage(null);
    try {
      await patch.mutateAsync({ id: candidateId, status });
      setMessage(status === "shortlisted" ? "Candidate shortlisted" : "Candidate rejected");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  }

  async function handleAssign() {
    if (!assignJobId) return;
    setError(null);
    setMessage(null);
    try {
      await assign.mutateAsync({ id: candidateId, jobDescriptionId: Number(assignJobId) });
      setMessage("Candidate assigned to job — scoring in progress.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Assign failed");
    }
  }

  async function handleDelete() {
    const label = candidate.data?.fullName?.trim() || `candidate #${candidateId}`;
    if (!window.confirm(`Remove ${label}? This cannot be undone.`)) return;
    setError(null);
    try {
      const jobId = candidate.data?.jobDescriptionId;
      await remove.mutateAsync(candidateId);
      if (jobId) {
        navigate(`/job-descriptions/${jobId}/candidates`);
      } else {
        navigate("/cv-screening/unassigned");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove candidate");
    }
  }

  if (candidate.isLoading || (isAssigned && evaluation.isLoading)) {
    return (
      <div className="page">
        <Spinner label="Loading evaluation" />
      </div>
    );
  }
  if (!candidate.data) {
    return <div className="page">Candidate not found.</div>;
  }

  const parsed = candidate.data.parsedData ?? {};
  const ev = evaluation.data;
  const cardStatus = ev ? recommendationStatus(ev.recommendation) : candidate.data.status;

  return (
    <>
      <PageHeader
        title={candidate.data.fullName ?? `Candidate #${candidate.data.id}`}
        breadcrumb="CV Screening / Candidate"
        actions={
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            {canDecide ? (
              <Button variant="destructive" disabled={remove.isPending} onClick={handleDelete}>
                {remove.isPending ? "Removing…" : "Remove Candidate"}
              </Button>
            ) : null}
            <Button variant="secondary" onClick={() => setPreviewOpen(true)}>
              View CV
            </Button>
            <Link
              to={
                isAssigned
                  ? `/job-descriptions/${candidate.data.jobDescriptionId}/candidates`
                  : "/cv-screening/unassigned"
              }
            >
              <Button variant="secondary">
                {isAssigned ? "Back to candidates" : "Back to unassigned CVs"}
              </Button>
            </Link>
          </div>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-4)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        {!isAssigned ? (
          <Card status="warning">
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", alignItems: "center" }}>
              <StatusBadge status="warning">Unassigned</StatusBadge>
              <span>
                This CV was fetched via{" "}
                {candidate.data.source === "webmail"
                  ? "Webmail"
                  : candidate.data.source === "outlook"
                    ? "Outlook"
                    : candidate.data.source === "whatsapp"
                      ? "WhatsApp"
                      : candidate.data.source === "gmail"
                        ? "Gmail"
                        : "the Google Form"}{" "}
                and hasn't been matched to a job yet.
              </span>
            </div>
            {candidate.data.matchReasoning ? (
              <p style={{ marginBottom: 0 }}>
                AI best guess: {candidate.data.matchReasoning}
                {candidate.data.matchConfidence != null ? (
                  <span className="font-data"> ({Math.round(candidate.data.matchConfidence * 100)}% confidence)</span>
                ) : null}
              </p>
            ) : null}
            <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-3)", alignItems: "center", flexWrap: "wrap" }}>
              <select
                className="form-field__input"
                style={{ minWidth: 220 }}
                value={assignJobId}
                onChange={(e) => setAssignJobId(e.target.value)}
              >
                <option value="">Pick a job…</option>
                {(openJobs.data?.items ?? []).map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title}
                  </option>
                ))}
              </select>
              <Button variant="primary" disabled={!assignJobId || assign.isPending} onClick={handleAssign}>
                Assign to job
              </Button>
            </div>
          </Card>
        ) : null}

        <Card status={cardStatus}>
          <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", alignItems: "center" }}>
            <StatusBadge status={candidate.data.status}>
              {CANDIDATE_STATUS_LABELS[candidate.data.status as keyof typeof CANDIDATE_STATUS_LABELS] ??
                candidate.data.status}
            </StatusBadge>
            {ev ? (
              <StatusBadge status={recommendationStatus(ev.recommendation)}>
                {ev.recommendationLabel}
              </StatusBadge>
            ) : null}
          </div>
          <p style={{ marginBottom: 0 }}>
            Email: {candidate.data.email ?? "—"} · Phone: {candidate.data.phone ?? "—"}
          </p>
          {ev ? (
            <p style={{ marginBottom: 0 }}>
              Role: <strong>{ev.jobTitle}</strong>
              {ev.ratingOutOf10 != null ? (
                <>
                  {" "}
                  · Rating: <span className="font-data">{ev.ratingOutOf10.toFixed(1)}/10</span>
                </>
              ) : null}
              {ev.overallScore != null ? (
                <>
                  {" "}
                  · Criteria score: <span className="font-data">{ev.overallScore.toFixed(1)}/100</span>
                </>
              ) : null}
              {ev.rankPosition != null ? (
                <>
                  {" "}
                  · Rank: <span className="font-data">#{ev.rankPosition}</span>
                </>
              ) : null}
            </p>
          ) : null}
        </Card>

        {ev ? (
          <Card status={recommendationStatus(ev.recommendation)}>
            <h3 style={{ marginTop: 0 }}>Screening recommendation</h3>
            {ev.ratingOutOf10 != null ? (
              <p style={{ marginTop: 0 }}>
                Fit vs job posting:{" "}
                <span className="font-data" style={{ fontSize: "var(--text-xl)" }}>
                  {ev.ratingOutOf10.toFixed(1)}/10
                </span>
              </p>
            ) : null}
            <p style={{ fontSize: "var(--text-md)", lineHeight: 1.55 }}>{ev.summary}</p>

            <h4>Why accepted</h4>
            <p style={{ lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
              {ev.whyAccepted || "—"}
            </p>
            {ev.strengths.length > 0 ? (
              <ul>
                {ev.strengths.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            ) : null}

            <h4>Why rejected</h4>
            <p style={{ lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
              {ev.whyRejected || "—"}
            </p>
            {ev.gaps.length > 0 ? (
              <ul>
                {ev.gaps.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            ) : null}

            {canDecide &&
            candidate.data.status !== "hired" &&
            candidate.data.status !== "shortlisted" &&
            candidate.data.status !== "rejected" ? (
              <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-3)" }}>
                <Button
                  variant="positive"
                  disabled={patch.isPending}
                  onClick={() => setStatus("shortlisted")}
                >
                  Accept / Shortlist
                </Button>
                <Button
                  variant="destructive"
                  disabled={patch.isPending}
                  onClick={() => setStatus("rejected")}
                >
                  Reject
                </Button>
              </div>
            ) : null}
          </Card>
        ) : isAssigned ? (
          <Card>
            <p>No evaluation available yet. Re-upload or re-rank after skills are set on the job.</p>
          </Card>
        ) : null}

        {ev && ev.skills.length > 0 ? (
          <Card>
            <h3 style={{ marginTop: 0 }}>Skill match (job level 1–10)</h3>
            <Table headers={["Skill", "Required level", "On CV?", "Notes"]}>
              {ev.skills.map((s) => (
                <tr key={s.skill} data-status={s.matched ? "positive" : "critical"}>
                  <td>{s.skill}</td>
                  <td className="font-data">{s.requiredLevel}/10</td>
                  <td>
                    <StatusBadge status={s.matched ? "shortlisted" : "rejected"}>
                      {s.matched ? "Matched" : "Missing"}
                    </StatusBadge>
                  </td>
                  <td>{s.notes ?? "—"}</td>
                </tr>
              ))}
            </Table>
          </Card>
        ) : null}

        <Card>
          <h3 style={{ marginTop: 0 }}>Parsed CV snapshot</h3>
          <p>
            Years experience:{" "}
            <span className="font-data">
              {String(parsed.years_experience ?? parsed.yearsExperience ?? "—")}
            </span>
          </p>
          <p>
            Skills extracted:{" "}
            {Array.isArray(parsed.skills) ? (parsed.skills as string[]).join(", ") : "—"}
          </p>
          <details>
            <summary>Raw CV text (excerpt)</summary>
            <pre
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "var(--font-data)",
                fontSize: "var(--text-xs)",
              }}
            >
              {String(parsed.raw_text ?? parsed.rawText ?? "").slice(0, 2000)}
            </pre>
          </details>
        </Card>
      </div>
      {previewOpen ? (
        <CvPreviewModal
          candidateId={candidate.data.id}
          candidateName={candidate.data.fullName ?? `Candidate #${candidate.data.id}`}
          parsedText={
            typeof parsed.rawText === "string"
              ? parsed.rawText
              : typeof parsed.raw_text === "string"
                ? parsed.raw_text
                : null
          }
          onClose={() => setPreviewOpen(false)}
        />
      ) : null}
    </>
  );
}
