import { apiRequest, getAccessToken } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type {
  AttendanceImportResult,
  AttendanceRecord,
  AttendanceRecordCreate,
  AttendanceRule,
  AttendanceSummary,
  LeaveRequest,
  LeaveRequestCreate,
} from "../types/attendance";

export async function listAttendanceRules(): Promise<AttendanceRule[]> {
  return apiRequest<AttendanceRule[]>("/attendance-rules");
}

export async function createAttendanceRule(payload: {
  name: string;
  shiftStart: string;
  shiftEnd: string;
  gracePeriodMinutes?: number;
  halfDayThresholdMinutes?: number;
  appliesToDepartmentId?: number | null;
}): Promise<AttendanceRule> {
  return apiRequest<AttendanceRule>("/attendance-rules", { method: "POST", body: payload });
}

export async function listAttendance(
  params: PaginationParams & {
    employeeId?: number;
    departmentId?: number;
    dateFrom?: string;
    dateTo?: string;
  } = {},
): Promise<PaginatedResponse<AttendanceRecord>> {
  return apiRequest<PaginatedResponse<AttendanceRecord>>("/attendance", { params });
}

export async function createAttendance(payload: AttendanceRecordCreate): Promise<AttendanceRecord> {
  return apiRequest<AttendanceRecord>("/attendance", { method: "POST", body: payload });
}

export async function updateAttendance(
  id: number,
  payload: {
    checkIn?: string | null;
    checkOut?: string | null;
    notes?: string | null;
    reason: string;
  },
): Promise<AttendanceRecord> {
  return apiRequest<AttendanceRecord>(`/attendance/${id}`, { method: "PATCH", body: payload });
}

export async function importAttendance(file: File): Promise<AttendanceImportResult> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<AttendanceImportResult>("/attendance/import", { method: "POST", formData: form });
}

export async function syncBiometric(): Promise<{ message: string; punchesFetched: number }> {
  return apiRequest("/attendance/sync-biometric", { method: "POST" });
}

export async function getAttendanceSummary(params: {
  employeeId: number;
  periodStart: string;
  periodEnd: string;
}): Promise<AttendanceSummary> {
  return apiRequest<AttendanceSummary>("/attendance/summary", { params });
}

export async function listLeaveRequests(
  params: PaginationParams & { employeeId?: number; status?: string; departmentId?: number } = {},
): Promise<PaginatedResponse<LeaveRequest>> {
  return apiRequest<PaginatedResponse<LeaveRequest>>("/leave-requests", { params });
}

export async function createLeaveRequest(payload: LeaveRequestCreate): Promise<LeaveRequest> {
  return apiRequest<LeaveRequest>("/leave-requests", { method: "POST", body: payload });
}

export async function updateLeaveRequest(
  id: number,
  payload: { status: "approved" | "rejected"; reason?: string },
): Promise<LeaveRequest> {
  return apiRequest<LeaveRequest>(`/leave-requests/${id}`, { method: "PATCH", body: payload });
}

/** Helper for template download (client-side only). */
export function attendanceImportTemplateCsv(): string {
  return "employee_code,date,check_in,check_out\nE001,2026-07-01,09:00,18:00\n";
}

void getAccessToken;
