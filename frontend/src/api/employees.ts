import { apiRequest, fetchBlob } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type {
  Department,
  DepartmentAiDraftRequest,
  DepartmentAiDraftResult,
  DepartmentCreate,
  DepartmentDocument,
  DepartmentDocumentKind,
  DepartmentUpdate,
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
import type { EducationVerificationResult } from "../types/educationVerification";

export async function listDepartments(): Promise<Department[]> {
  return apiRequest<Department[]>("/departments");
}

export async function getMyDepartment(): Promise<Department> {
  return apiRequest<Department>("/departments/me");
}

export async function createDepartment(payload: DepartmentCreate): Promise<Department> {
  return apiRequest<Department>("/departments", { method: "POST", body: payload });
}

export async function updateDepartment(
  id: number,
  payload: DepartmentUpdate,
): Promise<Department> {
  return apiRequest<Department>(`/departments/${id}`, { method: "PATCH", body: payload });
}

export async function deleteDepartment(id: number): Promise<void> {
  return apiRequest<void>(`/departments/${id}`, { method: "DELETE" });
}

export async function generateDepartmentAiDraft(
  payload: DepartmentAiDraftRequest,
): Promise<DepartmentAiDraftResult> {
  return apiRequest<DepartmentAiDraftResult>("/departments/ai-draft", {
    method: "POST",
    body: payload,
  });
}

export async function uploadDepartmentDocuments(
  departmentId: number,
  kind: DepartmentDocumentKind,
  files: File[],
): Promise<DepartmentDocument[]> {
  const form = new FormData();
  form.append("kind", kind);
  for (const file of files) form.append("files", file);
  return apiRequest<DepartmentDocument[]>(`/departments/${departmentId}/documents`, {
    method: "POST",
    formData: form,
  });
}

export async function downloadDepartmentDocument(
  departmentId: number,
  documentId: number,
): Promise<Blob> {
  return fetchBlob(`/departments/${departmentId}/documents/${documentId}/file`);
}

export async function deleteDepartmentDocument(
  departmentId: number,
  documentId: number,
): Promise<void> {
  return apiRequest<void>(`/departments/${departmentId}/documents/${documentId}`, {
    method: "DELETE",
  });
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

/** Education document upload + AI institution existence check. Not an official registry lookup. */
export async function verifyEducationDocuments(
  files: File[],
): Promise<EducationVerificationResult> {
  const form = new FormData();
  for (const file of files) {
    form.append("documents", file);
  }
  return apiRequest<EducationVerificationResult>("/education-documents/verify", {
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

export async function createEmployeeLetter(
  employeeId: number,
  kind: "appointment" | "contract",
): Promise<Blob> {
  return fetchBlob(`/employees/${employeeId}/letters/${kind}`, { method: "POST" });
}

export async function viewEmployeeLetter(
  employeeId: number,
  kind: "appointment" | "contract",
): Promise<Blob> {
  return fetchBlob(`/employees/${employeeId}/letters/${kind}`);
}

export interface LetterContent {
  employeeId: number;
  kind: string;
  filename: string;
  paragraphs: string[];
}

export async function getEmployeeLetterContent(
  employeeId: number,
  kind: "appointment" | "contract",
): Promise<LetterContent> {
  return apiRequest<LetterContent>(`/employees/${employeeId}/letters/${kind}/content`);
}

export async function saveEmployeeLetterContent(
  employeeId: number,
  kind: "appointment" | "contract",
  paragraphs: string[],
): Promise<LetterContent> {
  return apiRequest<LetterContent>(`/employees/${employeeId}/letters/${kind}/content`, {
    method: "PUT",
    body: { paragraphs },
  });
}

export interface LetterSignatureVerifyResult {
  verified: boolean;
  status: string;
  message: string;
  kind: string;
  employeeId: number;
  documentId: number | null;
}

/** Upload a PDF or photo of the signed letter; AI checks document type and signature. */
export async function verifyEmployeeLetterSignature(
  employeeId: number,
  kind: "appointment" | "contract",
  file: File,
): Promise<LetterSignatureVerifyResult> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<LetterSignatureVerifyResult>(
    `/employees/${employeeId}/letters/${kind}/verify`,
    { method: "POST", formData: form },
  );
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
