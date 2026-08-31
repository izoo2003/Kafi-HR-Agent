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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["attendance"] });
      qc.invalidateQueries({ queryKey: ["attendance-monthly-grid"] });
    },
  });
}

export function useImportAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.importAttendance(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["attendance"] });
      qc.invalidateQueries({ queryKey: ["attendance-monthly-grid"] });
    },
  });
}

export function useAttendancePeriodReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      saturdayOffMode,
      saturdayOffDate,
      extraHolidayDates,
    }: {
      file: File;
      saturdayOffMode?: "second_saturday" | "date";
      saturdayOffDate?: string | null;
      extraHolidayDates?: string[];
    }) =>
      api.uploadAttendancePeriodReport(file, {
        saturdayOffMode,
        saturdayOffDate,
        extraHolidayDates,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["attendance"] });
      qc.invalidateQueries({ queryKey: ["attendance-summary"] });
      qc.invalidateQueries({ queryKey: ["attendance-monthly-grid"] });
    },
  });
}

export function useCreateEmployeesFromAttendanceExcel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (people: { fullName: string; excelEmployeeId: string | null }[]) =>
      api.createEmployeesFromAttendanceExcel(people),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}

export function useMonthlyAttendanceGrid(params: { year: number; month: number } | null) {
  return useQuery({
    queryKey: ["attendance-monthly-grid", params],
    queryFn: () => api.getMonthlyAttendanceGrid(params!),
    enabled: Boolean(params),
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
