import { apiRequest, getAccessToken } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type {
  Department,
  DepartmentCreate,
  Employee,
  EmployeeCreate,
  EmployeeDetail,
  EmployeeDocument,
  EmployeeDocumentCategory,
  EmployeeReference,
  EmployeeReferenceCreate,
  EmployeeReferenceDocument,
  EmployeeReferenceUpdate,
  EmployeeUpdate,
} from "../types/employees";
import type { CnicVerificationResult } from "../types/cnic";

function apiBase(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";
  return raw.replace(/\/$/, "");
}

async function fetchBlob(path: string): Promise<Blob> {
  const token = getAccessToken();
  const base = apiBase();
  const url =
    base.startsWith("http://") || base.startsWith("https://")
      ? `${base}${path}`
      : `${base}${path}`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("File download failed");
  return res.blob();
}

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

/** CNIC document consistency check (format + image OCR). Not NADRA. Images only. */
export async function verifyCnic(
  typedCnic: string,
  images?: { front?: File | null; back?: File | null } | File | null,
): Promise<CnicVerificationResult> {
  const form = new FormData();
  form.append("typed_cnic", typedCnic);
  if (images && typeof images === "object" && !(images instanceof File)) {
    if (images.front) form.append("front_image", images.front);
    if (images.back) form.append("back_image", images.back);
  } else if (images instanceof File) {
    form.append("front_image", images);
  }
  return apiRequest<CnicVerificationResult>("/cnic/verify", {
    method: "POST",
    formData: form,
  });
}

export async function updateEmployee(id: number, payload: EmployeeUpdate): Promise<EmployeeDetail> {
  return apiRequest<EmployeeDetail>(`/employees/${id}`, { method: "PATCH", body: payload });
}

export async function getEmployee(id: number): Promise<EmployeeDetail> {
  return apiRequest<EmployeeDetail>(`/employees/${id}`);
}

/** Soft-exit: marks employee terminated (does not hard-delete the row). */
export async function exitEmployee(id: number): Promise<Employee> {
  return apiRequest<Employee>(`/employees/${id}`, { method: "DELETE" });
}

export async function uploadEmployeeDocuments(
  employeeId: number,
  params: { category: EmployeeDocumentCategory | string; title?: string; files: File[] },
): Promise<EmployeeDocument[]> {
  const form = new FormData();
  form.append("category", params.category);
  if (params.title) form.append("title", params.title);
  for (const f of params.files) form.append("files", f);
  return apiRequest<EmployeeDocument[]>(`/employees/${employeeId}/documents`, {
    method: "POST",
    formData: form,
  });
}

export async function deleteEmployeeDocument(employeeId: number, documentId: number): Promise<void> {
  return apiRequest<void>(`/employees/${employeeId}/documents/${documentId}`, { method: "DELETE" });
}

export async function downloadEmployeeDocument(
  employeeId: number,
  documentId: number,
): Promise<Blob> {
  return fetchBlob(`/employees/${employeeId}/documents/${documentId}/file`);
}

export async function createEmployeeReference(
  employeeId: number,
  payload: EmployeeReferenceCreate,
): Promise<EmployeeReference> {
  return apiRequest<EmployeeReference>(`/employees/${employeeId}/references`, {
    method: "POST",
    body: payload,
  });
}

export async function updateEmployeeReference(
  employeeId: number,
  referenceId: number,
  payload: EmployeeReferenceUpdate,
): Promise<EmployeeReference> {
  return apiRequest<EmployeeReference>(`/employees/${employeeId}/references/${referenceId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function deleteEmployeeReference(
  employeeId: number,
  referenceId: number,
): Promise<void> {
  return apiRequest<void>(`/employees/${employeeId}/references/${referenceId}`, {
    method: "DELETE",
  });
}

export async function uploadReferenceDocuments(
  employeeId: number,
  referenceId: number,
  files: File[],
): Promise<EmployeeReferenceDocument[]> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  return apiRequest<EmployeeReferenceDocument[]>(
    `/employees/${employeeId}/references/${referenceId}/documents`,
    { method: "POST", formData: form },
  );
}

export async function deleteReferenceDocument(
  employeeId: number,
  referenceId: number,
  documentId: number,
): Promise<void> {
  return apiRequest<void>(
    `/employees/${employeeId}/references/${referenceId}/documents/${documentId}`,
    { method: "DELETE" },
  );
}

export async function downloadReferenceDocument(
  employeeId: number,
  referenceId: number,
  documentId: number,
): Promise<Blob> {
  return fetchBlob(
    `/employees/${employeeId}/references/${referenceId}/documents/${documentId}/file`,
  );
}
