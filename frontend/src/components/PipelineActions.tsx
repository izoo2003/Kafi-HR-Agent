import { useState } from "react";
import { api } from "../api/client";

export function PipelineActions({ onCompleted }: { onCompleted: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(label: string, action: () => Promise<{ result?: Record<string, unknown>; message?: string }>) {
    setBusy(label);
    setError(null);
    setMessage(`${label} running in the background — Gmail/Gemini can take up to a couple of minutes…`);
    try {
      const state = await action();
      const detail = state.result && Object.keys(state.result).length > 0
        ? JSON.stringify(state.result)
        : state.message || "done";
      setMessage(`${label} finished — ${detail}`);
      onCompleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="pipeline-actions">
      <div className="pipeline-buttons">
        <button disabled={busy !== null} onClick={() => run("Fetch CVs", () => api.fetchSubmissions("all"))}>
          {busy === "Fetch CVs" ? "Fetching…" : "Fetch New CVs"}
        </button>
        <button disabled={busy !== null} onClick={() => run("Score", () => api.scorePending())}>
          {busy === "Score" ? "Scoring…" : "Score Pending"}
        </button>
        <button disabled={busy !== null} onClick={() => run("Rank", () => api.recomputeRanks())}>
          {busy === "Rank" ? "Ranking…" : "Recompute Ranks"}
        </button>
        <button
          className="primary"
          disabled={busy !== null}
          onClick={() => run("Run All", () => api.runFullPipeline())}
        >
          {busy === "Run All" ? "Running full pipeline…" : "Run Full Pipeline"}
        </button>
        <a className="button-link" href={api.masterReportUrl()}>
          Download Master Report
        </a>
      </div>
      {message && <p className="status-message success">{message}</p>}
      {error && <p className="status-message error">{error}</p>}
    </div>
  );
}
