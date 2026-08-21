import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/employeeTraining";
import type { TrainingCourseRecommendation, TrainingStatus } from "../types/employeeTraining";

export function useEmployeeTrainingList(employeeId?: number | null, enabled = true) {
  return useQuery({
    queryKey: ["employee-training", employeeId ?? "all"],
    queryFn: () =>
      api.listEmployeeTraining(
        employeeId != null ? { employeeId } : undefined,
      ),
    enabled,
    refetchOnWindowFocus: false,
  });
}

export function useRecommendEmployeeTraining() {
  return useMutation({
    mutationFn: (payload: { employeeId: number; topic: string }) =>
      api.recommendEmployeeTraining(payload),
  });
}

export function useAssignEmployeeTraining() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      employeeId: number;
      topic: string;
      courses: TrainingCourseRecommendation[];
    }) => api.assignEmployeeTraining(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["employee-training"] });
      qc.invalidateQueries({ queryKey: ["employee-training", vars.employeeId] });
    },
  });
}

export function useUpdateEmployeeTrainingStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { assignmentId: number; status: TrainingStatus }) =>
      api.updateEmployeeTrainingStatus(payload.assignmentId, payload.status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["employee-training"] });
    },
  });
}
