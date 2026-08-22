import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/employeeResignation";

export function useEmployeeResignations(employeeId?: number | null, enabled = true) {
  return useQuery({
    queryKey: ["employee-resignations", employeeId ?? "all"],
    queryFn: () =>
      api.listEmployeeResignations(
        employeeId != null ? { employeeId } : undefined,
      ),
    enabled,
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: false,
  });
}

export function useGenerateEmployeeResignation() {
  return useMutation({
    mutationFn: api.generateEmployeeResignation,
  });
}

export function useCreateEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createEmployeeResignation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-resignations"] }),
  });
}

export function useUpdateEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      noticeId,
      ...payload
    }: {
      noticeId: number;
      subject?: string;
      letterBody?: string;
      reason?: string | null;
      effectiveDate?: string | null;
      status?: "cancelled";
    }) => api.updateEmployeeResignation(noticeId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-resignations"] }),
  });
}

export function useDeleteEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noticeId: number) => api.deleteEmployeeResignation(noticeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-resignations"] }),
  });
}

export function useAcceptEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noticeId: number) => api.acceptEmployeeResignation(noticeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-resignations"] }),
  });
}
