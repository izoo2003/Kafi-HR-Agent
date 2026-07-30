export type KpiBand = "on_target" | "at_risk" | "below_target";
export type KpiReviewPeriod = "monthly" | "quarterly" | "annual";

export interface KpiDefinition {
  id: number;
  departmentId: number;
  name: string;
  description: string | null;
  measurementUnit: string | null;
  targetValue: string | number | null;
  weight: number | null;
  reviewPeriod: string | null;
  isArchived: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface KpiDefinitionCreate {
  departmentId: number;
  name: string;
  description?: string;
  measurementUnit?: string;
  targetValue: number;
  weight: number;
  reviewPeriod?: KpiReviewPeriod;
}

export interface KpiDefinitionUpdate {
  name?: string;
  description?: string | null;
  measurementUnit?: string | null;
  targetValue?: number;
  weight?: number;
  reviewPeriod?: KpiReviewPeriod;
}

export interface KpiEntry {
  id: number;
  kpiDefinitionId: number;
  employeeId: number;
  periodStart: string;
  periodEnd: string;
  actualValue: string | number;
  score: number | null;
  recordedBy: number;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface KpiEntryCreate {
  kpiDefinitionId: number;
  employeeId: number;
  periodStart: string;
  periodEnd: string;
  actualValue: number;
  notes?: string;
}

export interface KpiEntryUpdate {
  actualValue?: number;
  notes?: string | null;
}

export interface EmployeeKpiEntrySummary {
  kpiDefinitionId: number;
  name: string;
  target: number;
  actual: number;
  score: number;
  weight: number;
  band: KpiBand;
}

export interface EmployeeKpiSummary {
  employeeId: number;
  periodStart: string;
  periodEnd: string;
  overallScore: number;
  band: KpiBand;
  entries: EmployeeKpiEntrySummary[];
}

export interface DepartmentKpiBreakdown {
  kpiDefinitionId: number;
  name: string;
  averageScore: number;
  weight: number;
  band: KpiBand;
}

export interface DepartmentKpiSummary {
  departmentId: number;
  periodStart: string;
  periodEnd: string;
  overallScore: number;
  band: KpiBand;
  entriesRecorded: number;
  entriesExpected: number;
  completeness: number;
  employees: EmployeeKpiSummary[];
  kpiBreakdown: DepartmentKpiBreakdown[];
}
