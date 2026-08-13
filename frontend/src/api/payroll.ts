import { apiRequest } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type {
  PayrollComputeResult,
  PayrollSalaryRow,
  PayrollSalaryUpdate,
  TaxSlabInput,
  TaxYear,
  TaxYearCreate,
} from "../types/payroll";

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

export async function computePayroll(params: {
  periodMonth: number;
  periodYear: number;
  taxYearId: number;
}): Promise<PayrollComputeResult> {
  return apiRequest<PayrollComputeResult>("/payroll/compute", { params });
}

export async function listTaxYears(): Promise<TaxYear[]> {
  return apiRequest<TaxYear[]>("/payroll/tax-years");
}

export async function getTaxYear(id: number): Promise<TaxYear> {
  return apiRequest<TaxYear>(`/payroll/tax-years/${id}`);
}

export async function createTaxYear(payload: TaxYearCreate): Promise<TaxYear> {
  return apiRequest<TaxYear>("/payroll/tax-years", { method: "POST", body: payload });
}

export async function updateTaxYear(
  id: number,
  payload: Partial<TaxYearCreate>,
): Promise<TaxYear> {
  return apiRequest<TaxYear>(`/payroll/tax-years/${id}`, { method: "PATCH", body: payload });
}

export async function replaceTaxSlabs(id: number, slabs: TaxSlabInput[]): Promise<TaxYear> {
  return apiRequest<TaxYear>(`/payroll/tax-years/${id}/slabs`, {
    method: "PUT",
    body: { slabs },
  });
}
