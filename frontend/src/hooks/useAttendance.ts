import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/attendance";
import type { AttendanceRecordCreate, LeaveRequestCreate } from "../types/attendance";
import type { PaginationParams } from "../types/common";

export function useAttendanceRules() {
  return useQuery({ queryKey: ["attendance-rules"], queryFn: () => api.listAttendanceRules() });
}

export function useAttendanceRecords(
  params: PaginationParams & {
    employeeId?: number;
    departmentId?: number;
    dateFrom?: string;
    dateTo?: string;
  },
) {
  return useQuery({
    queryKey: ["attendance", params],
    queryFn: () => api.listAttendance(params),
  });
}

export function useCreateAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AttendanceRecordCreate) => api.createAttendance(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["attendance"] }),
  });
}

export function useImportAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.importAttendance(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["attendance"] }),
  });
}

export function useLeaveRequests(
  params: PaginationParams & { employeeId?: number; status?: string; departmentId?: number },
) {
  return useQuery({
    queryKey: ["leave-requests", params],
    queryFn: () => api.listLeaveRequests(params),
  });
}

export function useCreateLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: LeaveRequestCreate) => api.createLeaveRequest(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leave-requests"] }),
  });
}

export function useUpdateLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...payload
    }: {
      id: number;
      status: "approved" | "rejected";
      reason?: string;
    }) => api.updateLeaveRequest(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave-requests"] });
      qc.invalidateQueries({ queryKey: ["attendance"] });
    },
  });
}

export function useAttendanceSummary(params: {
  employeeId: number;
  periodStart: string;
  periodEnd: string;
} | null) {
  return useQuery({
    queryKey: ["attendance-summary", params],
    queryFn: () => api.getAttendanceSummary(params!),
    enabled: Boolean(params?.employeeId),
  });
}
