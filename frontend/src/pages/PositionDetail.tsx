import { Fragment, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { CandidateRanking } from "../api/types";
import { VerdictBadge } from "../components/VerdictBadge";

export function PositionDetail() {
  const { position } = useParams<{ position: string }>();
  const [candidates, setCandidates] = useState<CandidateRanking[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!position) return;
    setLoading(true);
    api
      .listCandidates(position)
      .then(setCandidates)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load candidates"))
      .finally(() => setLoading(false));
  }, [position]);

  if (!position) return null;

  return (
    <div>
      <Link to="/" className="back-link">
        ← All positions
      </Link>
      <div className="page-header">
        <h1>{position}</h1>
        <p className="page-subtitle">Ranked candidates for this role, highest score first.</p>
      </div>

      <a className="button-link" href={api.positionReportUrl(position)}>
        Download Excel Report
      </a>

      {loading && <p>Loading…</p>}
      {error && <p className="status-message error">{error}</p>}

      {!loading && !error && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Candidate</th>
              <th>Score</th>
              <th>Verdict</th>
              <th>Email</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <Fragment key={c.application_id}>
                <tr>
                  <td>#{c.rank}</td>
                  <td>{c.candidate_name}</td>
                  <td>{c.score}</td>
                  <td>
                    <VerdictBadge verdict={c.verdict} />
                  </td>
                  <td>{c.email}</td>
                  <td>{c.source}</td>
                  <td>
                    <button
                      className="link-button"
                      onClick={() => setExpanded(expanded === c.application_id ? null : c.application_id)}
                    >
                      {expanded === c.application_id ? "Hide" : "Details"}
                    </button>
                  </td>
                </tr>
                {expanded === c.application_id && (
                  <tr className="detail-row">
                    <td colSpan={7}>
                      <div className="detail-grid">
                        <div>
                          <strong>Education</strong>
                          <p>{c.education_summary ?? "—"}</p>
                        </div>
                        <div>
                          <strong>Experience</strong>
                          <p>{c.experience_summary ?? "—"}</p>
                        </div>
                        <div>
                          <strong>Key Strengths</strong>
                          <ul>
                            {c.key_strengths.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <strong>Why Select / Why Reject</strong>
                          <p>{c.hiring_summary ?? "—"}</p>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
