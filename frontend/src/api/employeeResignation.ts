import { apiRequest } from "./client";
import type {
  EmployeeResignation,
  EmployeeResignationGenerate,
  EmployeeResignationList,
} from "../types/employeeResignation";

export async function generateEmployeeResignation(payload: {
  employeeId?: number;
  reason?: string;
  effectiveDate?: string;
}): Promise<EmployeeResignationGenerate> {
  return apiRequest("/employee-resignations/generate", { method: "POST", body: payload });
}

export async function listEmployeeResignations(params?: {
  employeeId?: number;
}): Promise<EmployeeResignationList> {
  return apiRequest("/employee-resignations", {
    params: params?.employeeId != null ? { employeeId: params.employeeId } : undefined,
  });
}

export async function createEmployeeResignation(payload: {
  employeeId?: number;
  subject: string;
  letterBody: string;
  reason?: string;
  effectiveDate?: string;
  submit?: boolean;
}): Promise<EmployeeResignation> {
  return apiRequest("/employee-resignations", { method: "POST", body: payload });
}

export async function updateEmployeeResignation(
  noticeId: number,
  payload: {
    subject?: string;
    letterBody?: string;
    reason?: string | null;
    effectiveDate?: string | null;
    status?: "cancelled";
  },
): Promise<EmployeeResignation> {
  return apiRequest(`/employee-resignations/${noticeId}`, { method: "PATCH", body: payload });
}

export async function deleteEmployeeResignation(noticeId: number): Promise<{ message: string }> {
  return apiRequest(`/employee-resignations/${noticeId}`, { method: "DELETE" });
}

export async function submitEmployeeResignation(noticeId: number): Promise<EmployeeResignation> {
  return apiRequest(`/employee-resignations/${noticeId}/submit`, { method: "POST" });
}

export async function withdrawEmployeeResignation(noticeId: number): Promise<EmployeeResignation> {
  return apiRequest(`/employee-resignations/${noticeId}/withdraw`, { method: "POST" });
}

export async function acceptEmployeeResignation(noticeId: number): Promise<EmployeeResignation> {
  return apiRequest(`/employee-resignations/${noticeId}/accept`, { method: "POST" });
}

export async function rejectEmployeeResignation(
  noticeId: number,
  reason?: string,
): Promise<EmployeeResignation> {
  return apiRequest(`/employee-resignations/${noticeId}/reject`, {
    method: "POST",
    body: { reason: reason || null },
  });
}
