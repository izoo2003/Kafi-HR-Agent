import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as empApi from "../api/employees";
import type {
  DepartmentCreate,
  EmployeeCreate,
  EmployeeDocumentCategory,
  EmployeeReferenceCreate,
  EmployeeReferenceUpdate,
  EmployeeUpdate,
} from "../types/employees";
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

export function useEmployee(id: number | undefined) {
  return useQuery({
    queryKey: ["employees", id],
    queryFn: () => empApi.getEmployee(id!),
    enabled: id != null && !Number.isNaN(id),
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
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["employees"] });
      qc.invalidateQueries({ queryKey: ["employees", vars.id] });
    },
  });
}

export function useExitEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => empApi.exitEmployee(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}

function invalidateEmployee(qc: ReturnType<typeof useQueryClient>, employeeId: number) {
  qc.invalidateQueries({ queryKey: ["employees", employeeId] });
  qc.invalidateQueries({ queryKey: ["employees"] });
}

export function useUploadEmployeeDocuments(employeeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      category: EmployeeDocumentCategory | string;
      title?: string;
      files: File[];
    }) => empApi.uploadEmployeeDocuments(employeeId, params),
    onSuccess: () => invalidateEmployee(qc, employeeId),
  });
}

export function useDeleteEmployeeDocument(employeeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: number) => empApi.deleteEmployeeDocument(employeeId, documentId),
    onSuccess: () => invalidateEmployee(qc, employeeId),
  });
}

export function useCreateEmployeeReference(employeeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: EmployeeReferenceCreate) =>
      empApi.createEmployeeReference(employeeId, payload),
    onSuccess: () => invalidateEmployee(qc, employeeId),
  });
}

export function useUpdateEmployeeReference(employeeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      referenceId,
      payload,
    }: {
      referenceId: number;
      payload: EmployeeReferenceUpdate;
    }) => empApi.updateEmployeeReference(employeeId, referenceId, payload),
    onSuccess: () => invalidateEmployee(qc, employeeId),
  });
}

export function useDeleteEmployeeReference(employeeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (referenceId: number) => empApi.deleteEmployeeReference(employeeId, referenceId),
    onSuccess: () => invalidateEmployee(qc, employeeId),
  });
}

export function useUploadReferenceDocuments(employeeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ referenceId, files }: { referenceId: number; files: File[] }) =>
      empApi.uploadReferenceDocuments(employeeId, referenceId, files),
    onSuccess: () => invalidateEmployee(qc, employeeId),
  });
}

export function useDeleteReferenceDocument(employeeId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      referenceId,
      documentId,
    }: {
      referenceId: number;
      documentId: number;
    }) => empApi.deleteReferenceDocument(employeeId, referenceId, documentId),
    onSuccess: () => invalidateEmployee(qc, employeeId),
  });
}
