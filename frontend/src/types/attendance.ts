export interface AttendanceRule {
  id: number;
  name: string;
  shiftStart: string;
  shiftEnd: string;
  gracePeriodMinutes: number;
  halfDayThresholdMinutes: number;
  appliesToDepartmentId: number | null;
}

export interface AttendanceRecord {
  id: number;
  employeeId: number;
  date: string;
  checkIn: string | null;
  checkOut: string | null;
  source: string;
  status: string;
  notes: string | null;
}

export interface AttendanceRecordCreate {
  employeeId: number;
  date: string;
  checkIn?: string | null;
  checkOut?: string | null;
  notes?: string | null;
}

export interface LeaveRequest {
  id: number;
  employeeId: number;
  leaveType: string;
  startDate: string;
  endDate: string;
  status: string;
  approvedBy: number | null;
  reason: string | null;
}

export interface LeaveRequestCreate {
  employeeId: number;
  leaveType: "annual" | "sick" | "unpaid" | "other";
  startDate: string;
  endDate: string;
  reason?: string;
}

export interface AttendanceSummary {
  employeeId: number;
  periodStart: string;
  periodEnd: string;
  daysPresent: number;
  daysLate: number;
  daysHalfDay: number;
  daysAbsent: number;
  daysOnLeave: number;
  totalWorkingDays: number;
  overtimeHours: number;
}

export interface AttendanceImportResult {
  imported: number;
  errors: { row: number; message: string }[];
}
