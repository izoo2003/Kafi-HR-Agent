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
  departmentName: string | null;
  roleTitle: string;
  baseSalary: string | number;
  perDayRate: string | number;
  daysPresent: number;
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
  lateDeductionAmount: string | number;
  halfDayDeduction: string | number;
  allowanceAmount: string | number;
  bonusAmount: string | number;
  loanDeductionAmount: string | number;
  advanceAmount: string | number;
  paymentMode: string | null;
  remarks: string | null;
  grossSalary: string | number;
  grossAfterAttendance: string | number;
  annualTaxableIncome: string | number;
  annualTax: string | number;
  monthlyTax: string | number;
  netSalary: string | number;
  netPayable: string | number;
  taxManual?: boolean;
  lateEvents: { date: string; checkInTime: string; note?: string }[];
  notes: string | null;
}

export interface PayrollTaxSlabLite {
  sortOrder: number;
  minAmount: string | number;
  maxAmount: string | number | null;
  fixedAmount: string | number;
  ratePercent: string | number;
  excessOver: string | number;
}

export interface PayrollComputeResult {
  periodMonth: number;
  periodYear: number;
  periodStart: string;
  periodEnd: string;
  taxYearId: number;
  taxYearLabel: string;
  monthDays: number;
  latesPerOff: number;
  companyName: string;
  taxSlabs: PayrollTaxSlabLite[];
  employees: PayrollComputeRow[];
  aiSummary?: PayrollAiSummary | null;
}

export interface PayrollAiSummary {
  periodMonth: number;
  periodYear: number;
  employeeCount: number;
  totalNetPayable: number;
  paymentModeCounts: Record<string, number>;
  summaryText: string;
  generatedAt?: string | null;
}

export interface PayrollSheetAdjustmentInput {
  employeeId: number;
  allowanceAmount: number;
  bonusAmount: number;
  loanDeductionAmount: number;
  advanceAmount: number;
  paymentMode: string | null;
  remarks: string | null;
  baseSalary?: number | null;
  daysPresent?: number | null;
  daysAbsent?: number | null;
  daysLate?: number | null;
  daysHalfDay?: number | null;
  leaveUsed?: number | null;
  overtimeBonusDays?: number | null;
  monthlyTaxOverride?: number | null;
  excluded?: boolean;
}

export interface PayrollSheetAdjustmentsSave {
  periodMonth: number;
  periodYear: number;
  items: PayrollSheetAdjustmentInput[];
}
