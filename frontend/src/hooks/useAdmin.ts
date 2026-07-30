import { useQuery } from "@tanstack/react-query";
import * as adminApi from "../api/admin";
import type { PaginationParams } from "../types/common";

export function useAdminDashboard() {
  return useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () => adminApi.getAdminDashboard(),
  });
}

export function useAuditLogs(params: PaginationParams) {
  return useQuery({
    queryKey: ["admin", "audit-logs", params],
    queryFn: () => adminApi.listAuditLogs(params),
  });
}
