export interface PayrollSalaryRow {
  employeeId: number;
  employeeCode: string;
  fullName: string;
  departmentId: number;
  departmentName: string | null;
  roleTitle: string;
  status: string;
  baseSalary: string | number | null;
  updatedAt: string;
}

export interface PayrollSalaryUpdate {
  baseSalary: number | null;
}
