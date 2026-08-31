import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/hrPolicies";
import type { HrPoliciesDocument } from "../types/hrPolicies";

export function useHrPolicies() {
  return useQuery({
    queryKey: ["hr-policies"],
    queryFn: api.getHrPolicies,
  });
}

export function useSaveHrPolicies() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: HrPoliciesDocument) => api.saveHrPolicies(payload),
    onSuccess: (data) => {
      qc.setQueryData(["hr-policies"], data);
    },
  });
}
