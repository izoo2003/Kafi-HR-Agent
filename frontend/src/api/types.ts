// Mirrors backend/app/api/schemas.py — keep these two in sync.

export interface PositionSummary {
  position: string;
  candidates_scored: number;
  top_candidate: string | null;
  top_score: number | null;
  top_verdict: string | null;
}

export interface CandidateRanking {
  rank: number | null;
  application_id: number;
  candidate_name: string;
  email: string;
  phone: string | null;
  location: string | null;
  position: string;
  score: number | null;
  verdict: string | null;
  source: string;
  status: string;
  education_summary: string | null;
  experience_summary: string | null;
  key_strengths: string[];
  hiring_summary: string | null;
  submitted_at: string;
  scored_at: string | null;
}

export interface PipelineRunResult {
  new_applications: number;
  scored: number;
  failed: number;
  reports: string[];
}

export interface FetchResult {
  new_applications: number;
}

export interface ScoreResult {
  succeeded: number;
  failed: number;
}

export type SourceChannel = "gmail" | "google_form" | "whatsapp" | "all";

export interface JobState {
  status: "idle" | "running" | "succeeded" | "failed";
  action: string;
  message: string;
  result: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}
