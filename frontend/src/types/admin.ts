export interface AttendanceTodaySnapshot {
  present: number;
  absent: number;
  late: number;
  onLeave: number;
  halfDay: number;
  holiday: number;
  totalMarked: number;
}

export interface AdminDashboard {
  agentStatus: "ok" | "degraded" | "down";
  agentMode: "standalone" | "registered";
  registeredEmployeesActive: number;
  staffUsersActive: number;
  hrEmployeeRecordsActive: number;
  departments: number;
  openJobDescriptions: number;
  candidatesPendingReview: number;
  attendanceToday: AttendanceTodaySnapshot;
  leaveRequestsPending: number;
  payrollRunsPendingApproval: number;
}

export interface AuditLog {
  id: number;
  userId: number | null;
  action: string;
  entityType: string | null;
  entityId: number | null;
  timestamp: string;
}
