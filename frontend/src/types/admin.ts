export interface AuditLog {
  id: number;
  userId: number | null;
  action: string;
  entityType: string | null;
  entityId: number | null;
  timestamp: string;
}

export interface AdminDashboard {
  status: string;
  message?: string;
}
