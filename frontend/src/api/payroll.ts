import { apiRequest } from "./client";
import type { MessageResponse, PaginatedResponse, PaginationParams } from "../types/common";
import type { PayrollSalaryRow, PayrollSalaryUpdate } from "../types/payroll";

export async function listPayrollSalaries(
  params: PaginationParams = {},
): Promise<PaginatedResponse<PayrollSalaryRow>> {
  return apiRequest<PaginatedResponse<PayrollSalaryRow>>("/payroll/salaries", { params });
}

export async function updatePayrollSalary(
  employeeId: number,
  payload: PayrollSalaryUpdate,
): Promise<PayrollSalaryRow> {
  return apiRequest<PayrollSalaryRow>(`/payroll/salaries/${employeeId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function listPayrollRuns(): Promise<MessageResponse> {
  return apiRequest<MessageResponse>("/payroll-runs");
}
