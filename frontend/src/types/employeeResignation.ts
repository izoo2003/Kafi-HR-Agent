export type ResignationStatus = "pending" | "accepted" | "cancelled";

export interface EmployeeResignation {
  id: number;
  employeeId: number;
  employeeName: string | null;
  employeeCode: string | null;
  subject: string;
  letterBody: string;
  reason: string | null;
  effectiveDate: string | null;
  status: ResignationStatus;
  issuedBy: number;
  issuedAt: string;
  acceptedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EmployeeResignationGenerate {
  employeeId: number;
  employeeName: string;
  subject: string;
  letterBody: string;
  reason: string | null;
  effectiveDate: string | null;
}

export interface EmployeeResignationList {
  items: EmployeeResignation[];
  total: number;
}
