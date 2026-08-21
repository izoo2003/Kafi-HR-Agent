import { apiRequest } from "./client";
import type {
  EmployeePerformance,
  EmployeePerformanceAiSummary,
} from "../types/employeePerformance";

export async function getEmployeePerformance(params: {
  employeeId: number;
  periodYear: number;
  periodMonth: number;
}): Promise<EmployeePerformance> {
  return apiRequest<EmployeePerformance>("/employee-performance", {
    params: {
      employeeId: params.employeeId,
      periodYear: params.periodYear,
      periodMonth: params.periodMonth,
    },
  });
}

export async function generateEmployeePerformanceAiSummary(payload: {
  employeeId: number;
  periodYear: number;
  periodMonth: number;
}): Promise<EmployeePerformanceAiSummary> {
  return apiRequest<EmployeePerformanceAiSummary>("/employee-performance/ai-summary", {
    method: "POST",
    body: payload,
  });
}
