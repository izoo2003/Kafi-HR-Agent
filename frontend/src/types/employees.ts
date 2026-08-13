export interface Department {
  id: number;
  name: string;
  headEmployeeId: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface DepartmentCreate {
  name: string;
  headEmployeeId?: number | null;
}

export type EmployeeDocumentCategory = "cnic" | "education" | "other" | "photo";

export interface EmployeeDocument {
  id: number;
  employeeId: number;
  category: EmployeeDocumentCategory | string;
  title: string | null;
  originalFilename: string;
  mimeType: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EmployeeReferenceDocument {
  id: number;
  referenceId: number;
  originalFilename: string;
  mimeType: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EmployeeReference {
  id: number;
  employeeId: number;
  fullName: string;
  relation: string;
  phone: string | null;
  cnic: string | null;
  notes: string | null;
  documents: EmployeeReferenceDocument[];
  createdAt: string;
  updatedAt: string;
}

export interface EmployeeReferenceCreate {
  fullName: string;
  relation: string;
  phone?: string | null;
  cnic?: string | null;
  notes?: string | null;
}

export interface EmployeeReferenceUpdate {
  fullName?: string;
  relation?: string;
  phone?: string | null;
  cnic?: string | null;
  notes?: string | null;
}

export interface Employee {
  id: number;
  userId: number | null;
  employeeCode: string;
  fullName: string;
  departmentId: number;
  roleTitle: string;
  jobDescriptionText: string | null;
  employmentType: string | null;
  dateJoined: string | null;
  dateExited: string | null;
  status: string;
  baseSalary: string | number | null;
  managerId: number | null;

  cnic: string | null;
  email: string | null;
  personalMobile: string | null;
  alternateMobile: string | null;
  fatherName: string | null;
  dateOfBirth: string | null;
  gender: string | null;
  maritalStatus: string | null;
  currentAddress: string | null;
  permanentAddress: string | null;
  city: string | null;
  nationality: string | null;

  bankName: string | null;
  accountTitle: string | null;
  accountNumber: string | null;
  iban: string | null;
  branchName: string | null;
  branchCode: string | null;

  createdAt: string;
  updatedAt: string;
}

export interface EmployeeDetail extends Employee {
  documents: EmployeeDocument[];
  references: EmployeeReference[];
}

export interface EmployeeCreate {
  employeeCode: string;
  fullName: string;
  departmentId: number;
  roleTitle?: string | null;
  jobDescriptionText?: string | null;
  employmentType?: string;
  dateJoined?: string;
  baseSalary?: number;
  managerId?: number | null;
  userId?: number | null;
  status?: string;

  cnic?: string | null;
  email?: string | null;
  personalMobile?: string | null;
  alternateMobile?: string | null;
  fatherName?: string | null;
  dateOfBirth?: string | null;
  gender?: string | null;
  maritalStatus?: string | null;
  currentAddress?: string | null;
  permanentAddress?: string | null;
  city?: string | null;
  nationality?: string | null;

  bankName?: string | null;
  accountTitle?: string | null;
  accountNumber?: string | null;
  iban?: string | null;
  branchName?: string | null;
  branchCode?: string | null;
}

export interface EmployeeUpdate {
  fullName?: string;
  departmentId?: number;
  roleTitle?: string | null;
  jobDescriptionText?: string | null;
  employmentType?: string;
  dateJoined?: string | null;
  baseSalary?: number | null;
  managerId?: number | null;
  userId?: number | null;
  status?: string;

  cnic?: string | null;
  email?: string | null;
  personalMobile?: string | null;
  alternateMobile?: string | null;
  fatherName?: string | null;
  dateOfBirth?: string | null;
  gender?: string | null;
  maritalStatus?: string | null;
  currentAddress?: string | null;
  permanentAddress?: string | null;
  city?: string | null;
  nationality?: string | null;

  bankName?: string | null;
  accountTitle?: string | null;
  accountNumber?: string | null;
  iban?: string | null;
  branchName?: string | null;
  branchCode?: string | null;
}
