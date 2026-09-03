import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as payrollApi from "../api/payroll";
import type { PayrollSalaryUpdate, PayrollSheetAdjustmentsSave, TaxSlabInput, TaxYearCreate } from "../types/payroll";
import type { PaginationParams } from "../types/common";

export function usePayrollSalaries(params: PaginationParams = {}) {
  return useQuery({
    queryKey: ["payroll-salaries", params],
    queryFn: () => payrollApi.listPayrollSalaries(params),
  });
}

export function useUpdatePayrollSalary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      employeeId,
      payload,
    }: {
      employeeId: number;
      payload: PayrollSalaryUpdate;
    }) => payrollApi.updatePayrollSalary(employeeId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payroll-salaries"] });
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}

export function useTaxYears() {
  return useQuery({
    queryKey: ["tax-years"],
    queryFn: () => payrollApi.listTaxYears(),
  });
}

export function useCreateTaxYear() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaxYearCreate) => payrollApi.createTaxYear(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tax-years"] }),
  });
}

export function useUpdateTaxYear() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<TaxYearCreate> }) =>
      payrollApi.updateTaxYear(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tax-years"] }),
  });
}

export function useReplaceTaxSlabs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, slabs }: { id: number; slabs: TaxSlabInput[] }) =>
      payrollApi.replaceTaxSlabs(id, slabs),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tax-years"] }),
  });
}

export function usePayrollCompute(params: {
  periodMonth: number;
  periodYear: number;
  taxYearId: number;
} | null) {
  return useQuery({
    queryKey: ["payroll-compute", params],
    queryFn: () => payrollApi.computePayroll(params!),
    enabled: Boolean(params?.taxYearId && params.periodMonth && params.periodYear),
    refetchOnWindowFocus: false,
    staleTime: 5 * 60_000,
  });
}

export function useSavePayrollSheet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PayrollSheetAdjustmentsSave) =>
      payrollApi.savePayrollSheetAdjustments(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payroll-compute"] });
      qc.invalidateQueries({ queryKey: ["payroll-salaries"] });
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}

export function usePayrollAiSummary() {
  return useMutation({
    mutationFn: (params: { periodMonth: number; periodYear: number; taxYearId: number }) =>
      payrollApi.generatePayrollAiSummary(params),
  });
}
