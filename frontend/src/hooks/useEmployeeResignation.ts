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

function invalidateResignations(qc: ReturnType<typeof useQueryClient>) {
  return () => qc.invalidateQueries({ queryKey: ["employee-resignations"] });
}

export function useCreateEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createEmployeeResignation,
    onSuccess: invalidateResignations(qc),
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
    onSuccess: invalidateResignations(qc),
  });
}

export function useDeleteEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noticeId: number) => api.deleteEmployeeResignation(noticeId),
    onSuccess: invalidateResignations(qc),
  });
}

export function useSubmitEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noticeId: number) => api.submitEmployeeResignation(noticeId),
    onSuccess: invalidateResignations(qc),
  });
}

export function useWithdrawEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noticeId: number) => api.withdrawEmployeeResignation(noticeId),
    onSuccess: invalidateResignations(qc),
  });
}

export function useAcceptEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noticeId: number) => api.acceptEmployeeResignation(noticeId),
    onSuccess: invalidateResignations(qc),
  });
}

export function useRejectEmployeeResignation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ noticeId, reason }: { noticeId: number; reason?: string }) =>
      api.rejectEmployeeResignation(noticeId, reason),
    onSuccess: invalidateResignations(qc),
  });
}
