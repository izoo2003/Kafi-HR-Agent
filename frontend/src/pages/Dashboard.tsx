import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { PositionSummary } from "../api/types";
import { PipelineActions } from "../components/PipelineActions";
import { VerdictBadge } from "../components/VerdictBadge";

export function Dashboard() {
  const [positions, setPositions] = useState<PositionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listPositions()
      .then(setPositions)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load positions"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <div className="page-header">
        <h1>Open Positions</h1>
        <p className="page-subtitle">
          CV submissions ranked per role. Trigger the pipeline below to pull in new CVs and re-score.
        </p>
      </div>

      <PipelineActions onCompleted={load} />

      {loading && <p>Loading…</p>}
      {error && <p className="status-message error">{error}</p>}

      {!loading && !error && positions.length === 0 && (
        <div className="empty-state">
          No scored candidates yet. Run "Fetch New CVs" then "Score Pending" to get started.
        </div>
      )}

      {!loading && positions.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Position</th>
              <th>Candidates Scored</th>
              <th>Top Candidate</th>
              <th>Top Score</th>
              <th>Top Verdict</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.position}>
                <td>
                  <Link to={`/positions/${encodeURIComponent(p.position)}`} className="row-link">
                    {p.position}
                  </Link>
                </td>
                <td>{p.candidates_scored}</td>
                <td>{p.top_candidate ?? "—"}</td>
                <td>{p.top_score ?? "—"}</td>
                <td>
                  <VerdictBadge verdict={p.top_verdict} />
                </td>
                <td>
                  <a href={api.positionReportUrl(p.position)}>Download report</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
