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
  employeeName?: string | null;
  employeeCode?: string | null;
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

export interface LateEvent {
  date: string;
  checkInTime: string;
}

export interface DayClassification {
  date: string;
  dayType: string;
  weekday: string;
}

export interface UnmatchedAttendancePerson {
  fullName: string;
  excelEmployeeId: string | null;
}

export interface PeriodEmployeeReport {
  employeeId: number | null;
  employeeCode: string | null;
  excelEmployeeId: string | null;
  fullName: string;
  matchedEmployee: boolean;
  baseSalary: string | number | null;
  tenureMonths: number;
  leaveAllowance: number;
  leaveUsed: number;
  daysPresent: number;
  daysLate: number;
  daysHalfDay: number;
  daysSundayPresent: number;
  daysAbsent: number;
  absentsAfterLeave: number;
  lateOffDays: number;
  overtimeBonusDays: number;
  deductionDays: number;
  perDayRate: number;
  estimatedDeductionAmount: number;
  estimatedOvertimeAmount: number;
  estimatedNetSalary: number;
  lateEvents: LateEvent[];
  halfDayDates: string[];
  sundayDates: string[];
  absentDates: string[];
  overtimeDates: string[];
}

export interface AttendancePeriodReport {
  periodStart: string;
  periodEnd: string;
  monthDays: number;
  majorityAbsentThreshold: number;
  lateAfter: string;
  halfDayAfter: string;
  latesPerOff: number;
  importedRows: number;
  errors: { row: number; message: string }[];
  nonWorkingDays: DayClassification[];
  employees: PeriodEmployeeReport[];
  unmatchedPeople: UnmatchedAttendancePerson[];
}
