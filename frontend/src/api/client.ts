import type {
  CandidateRanking,
  JobState,
  PositionSummary,
  SourceChannel,
} from "./types";

// Empty = same origin (Vite proxy in dev). Override only if you intentionally
// call the API on another host.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  let response: Response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(
      `Failed to reach API at ${url || path}. ` +
        `Make sure backend is running (cd backend && python main.py) AND ` +
        `the Vite dev server was restarted after config changes.`,
    );
  }
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return (await response.json()) as T;
}

async function startAndWait(path: string, label: string): Promise<JobState> {
  const started = await request<JobState>(path, { method: "POST" });
  if (started.status !== "running") {
    return started;
  }

  const deadline = Date.now() + 5 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1500));
    const state = await request<JobState>("/pipeline/status");
    if (state.status === "succeeded" || state.status === "failed" || state.status === "idle") {
      if (state.status === "failed") {
        throw new Error(state.error || state.message || `${label} failed`);
      }
      return state;
    }
  }
  throw new Error(
    `${label} is still running after 5 minutes. Check the backend terminal logs, ` +
      `then refresh this page.`,
  );
}

export const api = {
  listPositions: () => request<PositionSummary[]>("/positions"),

  listCandidates: (position: string) =>
    request<CandidateRanking[]>(`/positions/${encodeURIComponent(position)}/candidates`),

  fetchSubmissions: (source: SourceChannel = "all") =>
    startAndWait(`/pipeline/fetch?source=${source}`, "fetch"),

  scorePending: () => startAndWait("/pipeline/score", "score"),

  recomputeRanks: () => startAndWait("/pipeline/rank", "rank"),

  runFullPipeline: () => startAndWait("/pipeline/run-all", "run-all"),

  getPipelineStatus: () => request<JobState>("/pipeline/status"),

  masterReportUrl: () => `${API_BASE_URL}/reports/master`,

  positionReportUrl: (position: string) =>
    `${API_BASE_URL}/reports/positions/${encodeURIComponent(position)}`,
};
