import { apiRequest } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type { AdminDashboard, AuditLog } from "../types/admin";

export async function getAdminDashboard(): Promise<AdminDashboard> {
  return apiRequest<AdminDashboard>("/admin/dashboard");
}

export async function listAuditLogs(
  params: PaginationParams = {},
): Promise<PaginatedResponse<AuditLog>> {
  return apiRequest<PaginatedResponse<AuditLog>>("/admin/audit-logs", { params });
}
