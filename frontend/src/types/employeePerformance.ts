export interface PerformanceKpiEntry {
  id: number;
  kpiDefinitionId: number;
  kpiName: string;
  measurementUnit: string | null;
  targetValue: string | number | null;
  weight: number | null;
  periodStart: string;
  periodEnd: string;
  actualValue: string | number;
  score: number | null;
  notes: string | null;
  createdAt: string;
}

export interface MonthlyPerformanceHistoryItem {
  periodYear: number;
  periodMonth: number;
  label: string;
  scoreOutOf10: number;
  entriesCount: number;
  finalized: boolean;
  aiSummary: string | null;
}

export interface EmployeePerformance {
  employeeId: number;
  employeeName: string;
  employeeCode: string;
  periodYear: number;
  periodMonth: number;
  periodLabel: string;
  isCurrentMonth: boolean;
  isFinalized: boolean;
  scoreOutOf10: number;
  overallPct: number | null;
  entriesCount: number;
  entries: PerformanceKpiEntry[];
  history: MonthlyPerformanceHistoryItem[];
  aiSummary: string | null;
}

export interface EmployeePerformanceAiSummary {
  employeeId: number;
  periodYear: number;
  periodMonth: number;
  scoreOutOf10: number;
  aiSummary: string;
}
