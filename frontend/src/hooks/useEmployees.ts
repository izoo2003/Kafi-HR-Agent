import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as empApi from "../api/employees";
import type { DepartmentCreate, EmployeeCreate, EmployeeUpdate } from "../types/employees";
import type { PaginationParams } from "../types/common";

export function useDepartments() {
  return useQuery({ queryKey: ["departments"], queryFn: () => empApi.listDepartments() });
}

export function useCreateDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DepartmentCreate) => empApi.createDepartment(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["departments"] }),
  });
}

export function useEmployees(
  params: PaginationParams & { departmentId?: number; status?: string; enabled?: boolean } = {},
) {
  const { enabled = true, ...filters } = params;
  return useQuery({
    queryKey: ["employees", filters],
    queryFn: () => empApi.listEmployees(filters),
    enabled,
  });
}

export function useCreateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: EmployeeCreate) => empApi.createEmployee(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}

export function useUpdateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: EmployeeUpdate }) =>
      empApi.updateEmployee(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}

export function useExitEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => empApi.exitEmployee(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}
