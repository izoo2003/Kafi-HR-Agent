import { apiRequest, fetchBlob, getAccessToken } from "./client";
import type { MessageResponse, PaginatedResponse, PaginationParams } from "../types/common";
import type {
  Candidate,
  CandidateEvaluation,
  CvSyncResult,
  JobDescription,
  JobDescriptionCreate,
  JobPostingAiDraftRequest,
  JobPostingAiDraftResult,
  JobPostingAiImageRequest,
  JobPostingAiImageResult,
  LinkedInAccount,
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

export async function generateJobPostingAiImage(
  payload: JobPostingAiImageRequest,
): Promise<JobPostingAiImageResult> {
  return apiRequest<JobPostingAiImageResult>("/job-descriptions/ai-image", {
    method: "POST",
    body: payload,
    timeoutMs: 180_000,
  });
}

export async function getApplicationFormUrl(): Promise<{ applicationFormUrl: string | null }> {
  return apiRequest<{ applicationFormUrl: string | null }>("/job-descriptions/application-form");
}

export async function listLinkedInAccounts(): Promise<LinkedInAccount[]> {
  return apiRequest<LinkedInAccount[]>("/job-descriptions/linkedin-accounts");
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

export async function deleteJobDescription(id: number): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(`/job-descriptions/${id}`, { method: "DELETE" });
}

export async function uploadJobImages(jobId: number, files: File[]): Promise<JobDescription> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return apiRequest<JobDescription>(`/job-descriptions/${jobId}/images`, {
    method: "POST",
    formData: form,
  });
}

export async function downloadJobImage(jobId: number, index: number): Promise<Blob> {
  return fetchBlob(`/job-descriptions/${jobId}/images/${index}/file`);
}

export async function deleteJobImage(jobId: number, index: number): Promise<JobDescription> {
  return apiRequest<JobDescription>(`/job-descriptions/${jobId}/images/${index}`, {
    method: "DELETE",
  });
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

export async function deleteCandidate(id: number): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(`/candidates/${id}`, { method: "DELETE" });
}

export async function downloadCandidateCv(candidateId: number): Promise<Blob> {
  return fetchBlob(`/candidates/${candidateId}/cv`);
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
