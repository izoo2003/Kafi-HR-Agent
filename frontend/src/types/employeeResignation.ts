export type ResignationStatus = "draft" | "pending" | "accepted" | "rejected" | "cancelled";
export type ResignationDirection = "hr" | "employee";

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
  direction: ResignationDirection;
  issuedBy: number;
  issuedAt: string;
  acceptedAt: string | null;
  rejectedAt: string | null;
  rejectionReason: string | null;
  reviewedBy: number | null;
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
  direction: ResignationDirection;
}

export interface EmployeeResignationList {
  items: EmployeeResignation[];
  total: number;
}
