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

export interface Employee {
  id: number;
  userId: number | null;
  employeeCode: string;
  fullName: string;
  departmentId: number;
  roleTitle: string;
  employmentType: string | null;
  dateJoined: string | null;
  dateExited: string | null;
  status: string;
  baseSalary: string | number | null;
  managerId: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface EmployeeCreate {
  employeeCode: string;
  fullName: string;
  departmentId: number;
  roleTitle: string;
  employmentType?: string;
  dateJoined?: string;
  baseSalary?: number;
  managerId?: number | null;
  userId?: number | null;
  status?: string;
}

export interface EmployeeUpdate {
  fullName?: string;
  departmentId?: number;
  roleTitle?: string;
  employmentType?: string;
  dateJoined?: string | null;
  baseSalary?: number | null;
  managerId?: number | null;
  userId?: number | null;
  status?: string;
}
