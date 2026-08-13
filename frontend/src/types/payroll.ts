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

export interface TaxSlab {
  id: number;
  taxYearId: number;
  sortOrder: number;
  minAmount: string | number;
  maxAmount: string | number | null;
  fixedAmount: string | number;
  ratePercent: string | number;
  excessOver: string | number;
  createdAt: string;
  updatedAt: string;
}

export interface TaxSlabInput {
  sortOrder: number;
  minAmount: number;
  maxAmount: number | null;
  fixedAmount: number;
  ratePercent: number;
  excessOver: number;
}

export interface TaxYear {
  id: number;
  label: string;
  startDate: string;
  endDate: string;
  isActive: boolean;
  notes: string | null;
  slabs: TaxSlab[];
  createdAt: string;
  updatedAt: string;
}

export interface TaxYearCreate {
  label: string;
  startDate: string;
  endDate: string;
  isActive?: boolean;
  notes?: string | null;
  slabs?: TaxSlabInput[];
}

export interface PayrollComputeRow {
  employeeId: number;
  employeeCode: string;
  fullName: string;
  baseSalary: string | number;
  perDayRate: string | number;
  daysAbsent: number;
  daysLate: number;
  daysHalfDay: number;
  lateOffDays: number;
  leaveAllowance: number;
  leaveUsed: number;
  absentsAfterLeave: number;
  overtimeBonusDays: number;
  attendanceDeduction: string | number;
  overtimeAmount: string | number;
  grossAfterAttendance: string | number;
  annualTaxableIncome: string | number;
  annualTax: string | number;
  monthlyTax: string | number;
  netSalary: string | number;
  lateEvents: { date: string; checkInTime: string; note?: string }[];
  notes: string | null;
}

export interface PayrollComputeResult {
  periodMonth: number;
  periodYear: number;
  periodStart: string;
  periodEnd: string;
  taxYearId: number;
  taxYearLabel: string;
  monthDays: number;
  employees: PayrollComputeRow[];
}
