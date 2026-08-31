import { apiRequest, getAccessToken } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type {
  AttendanceImportResult,
  AttendanceMonthlyGrid,
  AttendancePeriodReport,
  AttendanceRecord,
  AttendanceRecordCreate,
  AttendanceRule,
  AttendanceSummary,
  LeaveRequest,
  LeaveRequestCreate,
  UnmatchedAttendancePerson,
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

export async function uploadAttendancePeriodReport(
  file: File,
  options: {
    saturdayOffMode?: "second_saturday" | "date";
    saturdayOffDate?: string | null;
    extraHolidayDates?: string[];
  } = {},
): Promise<AttendancePeriodReport> {
  const form = new FormData();
  form.append("file", file);
  form.append("saturday_off_mode", options.saturdayOffMode ?? "second_saturday");
  if (options.saturdayOffDate) {
    form.append("saturday_off_date", options.saturdayOffDate);
  }
  const extras = (options.extraHolidayDates ?? []).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d));
  if (extras.length > 0) {
    form.append("extra_holiday_dates", extras.join(","));
  }
  return apiRequest<AttendancePeriodReport>("/attendance/period-report", {
    method: "POST",
    formData: form,
  });
}

export async function createEmployeesFromAttendanceExcel(
  people: UnmatchedAttendancePerson[],
): Promise<{ created: number; skipped: string[]; employees: UnmatchedAttendancePerson[] }> {
  return apiRequest("/attendance/period-report/create-employees", {
    method: "POST",
    body: { people },
  });
}

export async function getMonthlyAttendanceGrid(params: {
  year: number;
  month: number;
  departmentId?: number;
}): Promise<AttendanceMonthlyGrid> {
  return apiRequest<AttendanceMonthlyGrid>("/attendance/monthly/grid", { params });
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
  return (
    "name,date,check_in,check_out\n" +
    "Ali Khan,2026-07-01,09:35,18:00\n" +
    "Ali Khan,2026-07-02,09:45,18:05\n"
  );
}

void getAccessToken;
