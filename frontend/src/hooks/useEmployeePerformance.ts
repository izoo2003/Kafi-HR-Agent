import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as perfApi from "../api/employeePerformance";

export function useEmployeePerformance(
  params: { employeeId: number; periodYear: number; periodMonth: number } | null,
) {
  return useQuery({
    queryKey: ["employee-performance", params],
    queryFn: () => perfApi.getEmployeePerformance(params!),
    enabled: Boolean(params?.employeeId && params.periodYear && params.periodMonth),
    refetchOnWindowFocus: false,
  });
}

export function useEmployeePerformanceAiSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      employeeId: number;
      periodYear: number;
      periodMonth: number;
    }) => perfApi.generateEmployeePerformanceAiSummary(payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: [
          "employee-performance",
          {
            employeeId: vars.employeeId,
            periodYear: vars.periodYear,
            periodMonth: vars.periodMonth,
          },
        ],
      });
      qc.invalidateQueries({ queryKey: ["employee-performance"] });
    },
  });
}
