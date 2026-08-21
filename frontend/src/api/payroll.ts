import { apiRequest, getAccessToken } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type {
  PayrollAiSummary,
  PayrollComputeResult,
  PayrollSalaryRow,
  PayrollSalaryUpdate,
  PayrollSheetAdjustmentsSave,
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

export async function savePayrollSheetAdjustments(
  payload: PayrollSheetAdjustmentsSave,
): Promise<{ message: string; saved: number }> {
  return apiRequest("/payroll/sheet-adjustments", { method: "PUT", body: payload });
}

export async function downloadSalarySheetExcel(params: {
  periodMonth: number;
  periodYear: number;
  taxYearId: number;
}): Promise<Blob> {
  const token = getAccessToken();
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";
  const base = raw.replace(/\/$/, "");
  const qs = new URLSearchParams({
    period_month: String(params.periodMonth),
    period_year: String(params.periodYear),
    tax_year_id: String(params.taxYearId),
  });
  const url = `${base}/payroll/compute/export?${qs.toString()}`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Salary sheet download failed");
  return res.blob();
}

export async function generatePayrollAiSummary(params: {
  periodMonth: number;
  periodYear: number;
  taxYearId: number;
}): Promise<PayrollAiSummary> {
  return apiRequest<PayrollAiSummary>("/payroll/compute/ai-summary", {
    method: "POST",
    params: {
      periodMonth: params.periodMonth,
      periodYear: params.periodYear,
      taxYearId: params.taxYearId,
    },
  });
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
