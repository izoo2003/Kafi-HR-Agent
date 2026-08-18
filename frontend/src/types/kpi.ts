export type KpiBand = "on_target" | "at_risk" | "below_target" | "complete";
export type KpiReviewPeriod = "monthly" | "quarterly" | "annual";

export interface KpiDefinition {
  id: number;
  departmentId: number;
  ownerEmployeeId: number | null;
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
  departmentId?: number;
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

export interface EmployeeWorkItem {
  text: string;
  workDate?: string | null;
  points?: number | null;
}

export interface EmployeeKpiSummary {
  employeeId: number;
  departmentId: number;
  periodStart: string;
  periodEnd: string;
  submissionCount: number;
  contributionScore: number;
  departmentScore: number;
  departmentBand: KpiBand;
  globalScore: number;
  globalBand: KpiBand;
  workItems: EmployeeWorkItem[];
}

export interface DepartmentEmployeeKpiSummary {
  employeeId: number;
  employeeName: string;
  submissionCount: number;
  contributionScore: number;
  band: KpiBand;
  workItems: EmployeeWorkItem[];
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
  employees: DepartmentEmployeeKpiSummary[];
}

export interface GlobalDepartmentKpiSummary {
  departmentId: number;
  departmentName: string;
  overallScore: number;
  band: KpiBand;
  entriesRecorded: number;
  entriesExpected: number;
  completeness: number;
}

export interface GlobalKpiSummary {
  periodStart: string;
  periodEnd: string;
  overallScore: number;
  band: KpiBand;
  departmentsComplete: number;
  departmentsExpected: number;
  entriesRecorded: number;
  entriesExpected: number;
  completeness: number;
  departments: GlobalDepartmentKpiSummary[];
}

export interface KpiDailyPoint {
  date: string;
  score: number;
  band: KpiBand;
  entriesRecorded: number;
}

export interface KpiDailySummary {
  scope: "global" | "department";
  departmentId: number | null;
  departmentName: string | null;
  periodStart: string;
  periodEnd: string;
  overallScore: number;
  band: KpiBand;
  days: KpiDailyPoint[];
}

export interface KpiWorkLog {
  id: number;
  employeeId: number;
  employeeName: string;
  departmentId: number;
  departmentName: string;
  workDate: string;
  text: string;
  points: number;
  createdAt: string;
}
