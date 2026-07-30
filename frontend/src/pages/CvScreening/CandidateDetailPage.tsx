import { Link, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import {
  useCandidate,
  useCandidateEvaluation,
  usePatchCandidate,
} from "../../hooks/useJobDescriptions";
import { CANDIDATE_STATUS_LABELS } from "../../constants/statusLabels";
import { ApiError } from "../../api/client";
import { useState } from "react";
import { useAuth } from "../../hooks/useAuth";

function recommendationStatus(rec: string): string {
  if (rec === "shortlist") return "shortlisted";
  if (rec === "reject") return "rejected";
  return "pending";
}

export function CandidateDetailPage() {
  const { id } = useParams();
  const candidateId = Number(id);
  const { hasPermission } = useAuth();
  const canDecide = hasPermission("cv_screening", "write");
  const candidate = useCandidate(candidateId);
  const evaluation = useCandidateEvaluation(candidateId);
  const patch = usePatchCandidate();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

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

  if (candidate.isLoading || evaluation.isLoading) {
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
          <Link to={`/job-descriptions/${candidate.data.jobDescriptionId}/candidates`}>
            <Button variant="secondary">Back to candidates</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-4)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

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
              {ev.overallScore != null ? (
                <>
                  {" "}
                  · Score: <span className="font-data">{ev.overallScore.toFixed(1)}/100</span>
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
            <p style={{ fontSize: "var(--text-md)", lineHeight: 1.55 }}>{ev.summary}</p>

            {ev.strengths.length > 0 ? (
              <>
                <h4>Why accept / strengths</h4>
                <ul>
                  {ev.strengths.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </>
            ) : null}

            {ev.gaps.length > 0 ? (
              <>
                <h4>Why reject / gaps</h4>
                <ul>
                  {ev.gaps.map((g) => (
                    <li key={g}>{g}</li>
                  ))}
                </ul>
              </>
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
        ) : (
          <Card>
            <p>No evaluation available yet. Re-upload or re-rank after skills are set on the job.</p>
          </Card>
        )}

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
    </>
  );
}
