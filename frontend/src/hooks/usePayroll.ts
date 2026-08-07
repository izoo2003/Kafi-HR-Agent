import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as payrollApi from "../api/payroll";
import type { PayrollSalaryUpdate } from "../types/payroll";
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
