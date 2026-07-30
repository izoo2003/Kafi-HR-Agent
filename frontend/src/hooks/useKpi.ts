import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/kpi";
import type { KpiDefinitionCreate, KpiDefinitionUpdate, KpiEntryCreate } from "../types/kpi";

export function useKpiDefinitions(params?: {
  departmentId?: number;
  includeArchived?: boolean;
}) {
  return useQuery({
    queryKey: ["kpi-definitions", params],
    queryFn: () => api.listKpiDefinitions(params),
  });
}

export function useCreateKpiDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: KpiDefinitionCreate) => api.createKpiDefinition(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kpi-definitions"] }),
  });
}

export function useUpdateKpiDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: KpiDefinitionUpdate }) =>
      api.updateKpiDefinition(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kpi-definitions"] }),
  });
}

export function useArchiveKpiDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.archiveKpiDefinition(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kpi-definitions"] }),
  });
}

export function useDepartmentKpiSummary(
  departmentId: number | null,
  periodStart: string,
  periodEnd: string,
) {
  return useQuery({
    queryKey: ["kpi-dept-summary", departmentId, periodStart, periodEnd],
    queryFn: () => api.getDepartmentKpiSummary(departmentId!, periodStart, periodEnd),
    enabled: departmentId != null && !!periodStart && !!periodEnd,
  });
}

export function useEmployeeKpiSummary(
  employeeId: number | null,
  periodStart: string,
  periodEnd: string,
) {
  return useQuery({
    queryKey: ["kpi-emp-summary", employeeId, periodStart, periodEnd],
    queryFn: () => api.getEmployeeKpiSummary(employeeId!, periodStart, periodEnd),
    enabled: employeeId != null && !!periodStart && !!periodEnd,
  });
}

export function useCreateKpiEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: KpiEntryCreate) => api.createKpiEntry(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-dept-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-emp-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-entries"] });
    },
  });
}

export function useMarkKpiPeriodReviewed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { departmentId: number; periodStart: string; periodEnd: string }) =>
      api.markKpiPeriodReviewed(args.departmentId, args.periodStart, args.periodEnd),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kpi-dept-summary"] }),
  });
}
