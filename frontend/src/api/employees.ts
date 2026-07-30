import { apiRequest } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type {
  Department,
  DepartmentCreate,
  Employee,
  EmployeeCreate,
  EmployeeUpdate,
} from "../types/employees";

export async function listDepartments(): Promise<Department[]> {
  return apiRequest<Department[]>("/departments");
}

export async function createDepartment(payload: DepartmentCreate): Promise<Department> {
  return apiRequest<Department>("/departments", { method: "POST", body: payload });
}

export async function listEmployees(
  params: PaginationParams & { departmentId?: number; status?: string } = {},
): Promise<PaginatedResponse<Employee>> {
  return apiRequest<PaginatedResponse<Employee>>("/employees", { params });
}

export async function createEmployee(payload: EmployeeCreate): Promise<Employee> {
  return apiRequest<Employee>("/employees", { method: "POST", body: payload });
}

export async function updateEmployee(id: number, payload: EmployeeUpdate): Promise<Employee> {
  return apiRequest<Employee>(`/employees/${id}`, { method: "PATCH", body: payload });
}

export async function getEmployee(id: number): Promise<Employee> {
  return apiRequest<Employee>(`/employees/${id}`);
}

/** Soft-exit: marks employee terminated (does not hard-delete the row). */
export async function exitEmployee(id: number): Promise<Employee> {
  return apiRequest<Employee>(`/employees/${id}`, { method: "DELETE" });
}
