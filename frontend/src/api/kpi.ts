import { apiRequest } from "./client";
import type { PaginatedResponse } from "../types/common";
import type {
  DepartmentKpiSummary,
  EmployeeKpiSummary,
  KpiDefinition,
  KpiDefinitionCreate,
  KpiDefinitionUpdate,
  KpiEntry,
  KpiEntryCreate,
  KpiEntryUpdate,
} from "../types/kpi";

export function listKpiDefinitions(params?: {
  departmentId?: number;
  includeArchived?: boolean;
}): Promise<KpiDefinition[]> {
  return apiRequest<KpiDefinition[]>("/kpi-definitions", { params });
}

export function createKpiDefinition(payload: KpiDefinitionCreate): Promise<KpiDefinition> {
  return apiRequest<KpiDefinition>("/kpi-definitions", { method: "POST", body: payload });
}

export function updateKpiDefinition(
  id: number,
  payload: KpiDefinitionUpdate,
): Promise<KpiDefinition> {
  return apiRequest<KpiDefinition>(`/kpi-definitions/${id}`, { method: "PATCH", body: payload });
}

export function archiveKpiDefinition(id: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/kpi-definitions/${id}`, { method: "DELETE" });
}

export function listKpiEntries(params?: {
  page?: number;
  pageSize?: number;
  employeeId?: number;
  departmentId?: number;
  periodStart?: string;
  periodEnd?: string;
}): Promise<PaginatedResponse<KpiEntry>> {
  return apiRequest<PaginatedResponse<KpiEntry>>("/kpi-entries", { params });
}

export function createKpiEntry(payload: KpiEntryCreate): Promise<KpiEntry> {
  return apiRequest<KpiEntry>("/kpi-entries", { method: "POST", body: payload });
}

export function updateKpiEntry(id: number, payload: KpiEntryUpdate): Promise<KpiEntry> {
  return apiRequest<KpiEntry>(`/kpi-entries/${id}`, { method: "PATCH", body: payload });
}

export function getEmployeeKpiSummary(
  employeeId: number,
  periodStart: string,
  periodEnd: string,
): Promise<EmployeeKpiSummary> {
  return apiRequest<EmployeeKpiSummary>(`/employees/${employeeId}/kpi-summary`, {
    params: { periodStart, periodEnd },
  });
}

export function getDepartmentKpiSummary(
  departmentId: number,
  periodStart: string,
  periodEnd: string,
): Promise<DepartmentKpiSummary> {
  return apiRequest<DepartmentKpiSummary>(`/departments/${departmentId}/kpi-summary`, {
    params: { periodStart, periodEnd },
  });
}

export function markKpiPeriodReviewed(
  departmentId: number,
  periodStart: string,
  periodEnd: string,
): Promise<{ message: string; departmentId: number; periodStart: string; periodEnd: string }> {
  return apiRequest(`/departments/${departmentId}/kpi-period-reviewed`, {
    method: "POST",
    body: { periodStart, periodEnd },
  });
}

export function seedKpiDefaults(departmentId: number): Promise<{
  message: string;
  created: KpiDefinition[];
  skippedExisting: string[];
}> {
  return apiRequest(`/departments/${departmentId}/kpi-definitions/seed-defaults`, {
    method: "POST",
  });
}

export function aiSuggestKpiEntry(payload: {
  departmentId: number;
  employeeId: number;
  periodStart: string;
  periodEnd: string;
  text: string;
}): Promise<{ kpiDefinitionId: number; actualValue: number; reasoning: string }> {
  return apiRequest("/kpi/ai-suggest-entry", { method: "POST", body: payload });
}
