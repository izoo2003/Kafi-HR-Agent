import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/kpi";
import type { KpiDefinitionCreate, KpiDefinitionUpdate, KpiEntryCreate } from "../types/kpi";

export function useKpiDefinitions(params?: {
  departmentId?: number;
  includeArchived?: boolean;
  enabled?: boolean;
}) {
  const { enabled = true, ...filters } = params ?? {};
  return useQuery({
    queryKey: ["kpi-definitions", filters],
    queryFn: () => api.listKpiDefinitions(filters),
    enabled,
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
    staleTime: 30_000,
  });
}

export function useGlobalKpiSummary(
  periodStart: string,
  periodEnd: string,
  enabled = true,
) {
  return useQuery({
    queryKey: ["kpi-global-summary", periodStart, periodEnd],
    queryFn: () => api.getGlobalKpiSummary(periodStart, periodEnd),
    enabled: enabled && !!periodStart && !!periodEnd,
    staleTime: 30_000,
  });
}

export function useKpiDailySummary(
  periodStart: string,
  periodEnd: string,
  departmentId?: number | null,
  enabled = true,
) {
  return useQuery({
    queryKey: ["kpi-daily-summary", periodStart, periodEnd, departmentId ?? null],
    queryFn: () =>
      api.getKpiDailySummary({
        periodStart,
        periodEnd,
        departmentId: departmentId ?? undefined,
      }),
    enabled: enabled && !!periodStart && !!periodEnd,
    staleTime: 30_000,
  });
}

export function useKpiWorkLogs(params: {
  periodStart: string;
  periodEnd: string;
  departmentId?: number | null;
  employeeId?: number | null;
  enabled?: boolean;
}) {
  const { periodStart, periodEnd, departmentId, employeeId, enabled = true } = params;
  return useQuery({
    queryKey: ["kpi-work-logs", periodStart, periodEnd, departmentId ?? null, employeeId ?? null],
    queryFn: () =>
      api.listKpiWorkLogs({
        periodStart,
        periodEnd,
        departmentId: departmentId ?? undefined,
        employeeId: employeeId ?? undefined,
      }),
    enabled: enabled && !!periodStart && !!periodEnd,
    staleTime: 30_000,
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
    staleTime: 30_000,
  });
}

export function useCreateKpiEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: KpiEntryCreate) => api.createKpiEntry(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-dept-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-emp-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-global-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-daily-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-work-logs"] });
      qc.invalidateQueries({ queryKey: ["kpi-entries"] });
    },
  });
}

export function useMarkKpiPeriodReviewed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { departmentId: number; periodStart: string; periodEnd: string }) =>
      api.markKpiPeriodReviewed(args.departmentId, args.periodStart, args.periodEnd),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-dept-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-global-summary"] });
    },
  });
}

export function useSeedKpiDefaults() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (departmentId: number) => api.seedKpiDefaults(departmentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-definitions"] });
      qc.invalidateQueries({ queryKey: ["kpi-dept-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-global-summary"] });
    },
  });
}

export function useAiSuggestKpiEntry() {
  return useMutation({
    mutationFn: api.aiSuggestKpiEntry,
  });
}

export function useCreateKpiWorkSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createKpiWorkSubmission,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-dept-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-emp-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-global-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-daily-summary"] });
      qc.invalidateQueries({ queryKey: ["kpi-work-logs"] });
      qc.invalidateQueries({ queryKey: ["kpi-entries"] });
    },
  });
}
