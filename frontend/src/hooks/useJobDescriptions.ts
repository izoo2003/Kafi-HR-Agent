import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as jdApi from "../api/jobDescriptions";
import type { JobDescriptionCreate, ScoringCriteriaInput } from "../types/cvScreening";
import type { PaginationParams } from "../types/common";

export function useJobDescriptions(
  params: PaginationParams & { departmentId?: number; status?: string } = {},
) {
  return useQuery({
    queryKey: ["job-descriptions", params],
    queryFn: () => jdApi.listJobDescriptions(params),
  });
}

export function useJobDescription(id: number) {
  return useQuery({
    queryKey: ["job-descriptions", id],
    queryFn: () => jdApi.getJobDescription(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useCreateJobDescription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobDescriptionCreate) => jdApi.createJobDescription(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["job-descriptions"] }),
  });
}

export function useUpdateJobDescription(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<JobDescriptionCreate>) => jdApi.updateJobDescription(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["job-descriptions"] });
      qc.invalidateQueries({ queryKey: ["job-descriptions", id] });
    },
  });
}

export function useCriteria(jobId: number) {
  return useQuery({
    queryKey: ["scoring-criteria", jobId],
    queryFn: () => jdApi.listCriteria(jobId),
    enabled: jobId > 0,
  });
}

export function useReplaceCriteria(jobId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (criteria: ScoringCriteriaInput[]) => jdApi.replaceCriteria(jobId, criteria),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scoring-criteria", jobId] }),
  });
}

export function useCandidates(jobId: number, params: PaginationParams = {}) {
  return useQuery({
    queryKey: ["candidates", jobId, params],
    queryFn: () => jdApi.listCandidates(jobId, params),
    enabled: jobId > 0,
  });
}

export function useUploadCandidates(jobId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => jdApi.uploadCandidates(jobId, files),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["candidates", jobId] });
      qc.invalidateQueries({ queryKey: ["ranking", jobId] });
    },
  });
}

export function useRanking(jobId: number) {
  return useQuery({
    queryKey: ["ranking", jobId],
    queryFn: () => jdApi.getRanking(jobId),
    enabled: jobId > 0,
  });
}

export function useCandidate(id: number) {
  return useQuery({
    queryKey: ["candidate", id],
    queryFn: () => jdApi.getCandidate(id),
    enabled: id > 0,
  });
}

export function useCandidateEvaluation(id: number) {
  return useQuery({
    queryKey: ["candidate-evaluation", id],
    queryFn: () => jdApi.getCandidateEvaluation(id),
    enabled: id > 0,
  });
}

export function usePatchCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number; status?: string; fullName?: string }) =>
      jdApi.patchCandidate(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["candidates", data.jobDescriptionId] });
      qc.invalidateQueries({ queryKey: ["ranking", data.jobDescriptionId] });
      qc.invalidateQueries({ queryKey: ["candidate", data.id] });
      qc.invalidateQueries({ queryKey: ["candidate-evaluation", data.id] });
    },
  });
}
