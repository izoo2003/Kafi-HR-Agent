import { apiRequest, getAccessToken } from "./client";
import type { MessageResponse, PaginatedResponse, PaginationParams } from "../types/common";
import type {
  Candidate,
  CandidateEvaluation,
  CvSyncResult,
  JobDescription,
  JobDescriptionCreate,
  JobPostingAiDraftRequest,
  JobPostingAiDraftResult,
  RankingRow,
  ScoringCriteria,
  ScoringCriteriaInput,
} from "../types/cvScreening";

export async function listJobDescriptions(
  params: PaginationParams & { departmentId?: number; status?: string } = {},
): Promise<PaginatedResponse<JobDescription>> {
  return apiRequest<PaginatedResponse<JobDescription>>("/job-descriptions", { params });
}

export async function createJobDescription(payload: JobDescriptionCreate): Promise<JobDescription> {
  return apiRequest<JobDescription>("/job-descriptions", { method: "POST", body: payload });
}

export async function generateJobPostingAiDraft(
  payload: JobPostingAiDraftRequest,
): Promise<JobPostingAiDraftResult> {
  return apiRequest<JobPostingAiDraftResult>("/job-descriptions/ai-draft", {
    method: "POST",
    body: payload,
  });
}

export async function getJobDescription(id: number): Promise<JobDescription> {
  return apiRequest<JobDescription>(`/job-descriptions/${id}`);
}

export async function updateJobDescription(
  id: number,
  payload: Partial<JobDescriptionCreate>,
): Promise<JobDescription> {
  return apiRequest<JobDescription>(`/job-descriptions/${id}`, { method: "PATCH", body: payload });
}

export async function listCriteria(jobId: number): Promise<ScoringCriteria[]> {
  return apiRequest<ScoringCriteria[]>(`/job-descriptions/${jobId}/scoring-criteria`);
}

export async function replaceCriteria(
  jobId: number,
  criteria: ScoringCriteriaInput[],
): Promise<ScoringCriteria[]> {
  return apiRequest<ScoringCriteria[]>(`/job-descriptions/${jobId}/scoring-criteria`, {
    method: "POST",
    body: { criteria },
  });
}

export async function listCandidates(
  jobId: number,
  params: PaginationParams = {},
): Promise<PaginatedResponse<Candidate>> {
  return apiRequest<PaginatedResponse<Candidate>>(`/job-descriptions/${jobId}/candidates`, {
    params,
  });
}

export async function uploadCandidates(jobId: number, files: File[]): Promise<Candidate[]> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  return apiRequest<Candidate[]>(`/job-descriptions/${jobId}/candidates`, {
    method: "POST",
    formData: form,
  });
}

export async function getCandidate(id: number): Promise<Candidate> {
  return apiRequest<Candidate>(`/candidates/${id}`);
}

export async function getCandidateEvaluation(id: number): Promise<CandidateEvaluation> {
  return apiRequest<CandidateEvaluation>(`/candidates/${id}/evaluation`);
}

export async function patchCandidate(
  id: number,
  payload: { status?: string; fullName?: string },
): Promise<Candidate> {
  return apiRequest<Candidate>(`/candidates/${id}`, { method: "PATCH", body: payload });
}

export async function getRanking(jobId: number): Promise<RankingRow[]> {
  return apiRequest<RankingRow[]>(`/job-descriptions/${jobId}/ranking`);
}

export async function rerank(jobId: number): Promise<RankingRow[]> {
  return apiRequest<RankingRow[]>(`/job-descriptions/${jobId}/rank`, { method: "POST" });
}

export async function downloadReport(jobId: number): Promise<Blob> {
  const token = getAccessToken();
  const res = await fetch(`/api/v1/job-descriptions/${jobId}/report`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Report download failed");
  return res.blob();
}

export async function scoreOverride(
  candidateId: number,
  payload: { scoringCriteriaId: number; rawScore: number; reason: string },
): Promise<MessageResponse> {
  return apiRequest(`/candidates/${candidateId}/score-override`, {
    method: "POST",
    body: payload,
  });
}

export async function syncCvSources(): Promise<CvSyncResult> {
  return apiRequest<CvSyncResult>("/cv-screening/sync", { method: "POST" });
}

export async function listUnassignedCandidates(
  params: PaginationParams = {},
): Promise<PaginatedResponse<Candidate>> {
  return apiRequest<PaginatedResponse<Candidate>>("/candidates/unassigned", { params });
}

export async function assignCandidate(id: number, jobDescriptionId: number): Promise<Candidate> {
  return apiRequest<Candidate>(`/candidates/${id}/assign`, {
    method: "POST",
    body: { jobDescriptionId },
  });
}
