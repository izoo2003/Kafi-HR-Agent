import type { PayrollComputeResult, PayrollComputeRow, TaxSlabInput } from "../types/payroll";

/** Canonical salary sheet payment modes (dropdown). */
export const SALARY_PAYMENT_MODES = ["IBFT", "Cheque", "Cash"] as const;
export type SalaryPaymentMode = (typeof SALARY_PAYMENT_MODES)[number];

/** Map legacy/free-text values onto IBFT | Cheque | Cash. */
export function normalizePaymentMode(raw: string | null | undefined): SalaryPaymentMode {
  const v = (raw || "").trim().toLowerCase();
  if (!v || v === "ibft" || v === "bank" || v === "online") return "IBFT";
  if (v === "cheque" || v === "check" || v === "chq" || v === "cq") return "Cheque";
  if (v === "cash") return "Cash";
  return "IBFT";
}

export type SheetDraft = {
  baseSalary: string;
  daysPresent: string;
  daysAbsent: string;
  leaveUsed: string;
  daysLate: string;
  daysHalfDay: string;
  allowanceAmount: string;
  bonusAmount: string;
  loanDeductionAmount: string;
  advanceAmount: string;
  monthlyTax: string;
  taxManual: boolean;
  paymentMode: string;
  remarks: string;
};

export type LiveRow = {
  employeeId: number;
  fullName: string;
  roleTitle: string;
  employeeCode: string;
  leaveAllowance: number;
  leaveUsed: number;
  base: number;
  perDay: number;
  daysPresent: number;
  daysAbsent: number;
  daysLate: number;
  daysHalfDay: number;
  lateOffDays: number;
  allowance: number;
  bonus: number;
  gross: number;
  lateDed: number;
  halfDed: number;
  loan: number;
  advance: number;
  taxComputed: number;
  tax: number;
  net: number;
  paymentMode: string;
  remarks: string;
  draft: SheetDraft;
};

function n(value: string | number | null | undefined): number {
  const v = Number(value);
  return Number.isFinite(v) ? v : 0;
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

export function annualTax(income: number, slabs: TaxSlabInput[]): number {
  if (income <= 0 || slabs.length === 0) return 0;
  const ordered = [...slabs].sort((a, b) => a.sortOrder - b.sortOrder || a.minAmount - b.minAmount);
  const match =
    ordered.find((s) => s.maxAmount == null || income <= s.maxAmount) ?? ordered[ordered.length - 1];
  const excess = Math.max(0, income - match.excessOver);
  return round2(match.fixedAmount + (excess * match.ratePercent) / 100);
}

export function monthlyTaxFromGross(gross: number, slabs: TaxSlabInput[]): number {
  return round2(annualTax(gross * 12, slabs) / 12);
}

export function computeLiveRow(
  emp: PayrollComputeRow,
  draft: SheetDraft | undefined,
  opts: { monthDays: number; latesPerOff: number; slabs: TaxSlabInput[] },
): LiveRow {
  const d = draft;
  const monthDays = opts.monthDays || 30;
  const latesPerOff = opts.latesPerOff || 3;
  const base = d ? n(d.baseSalary) : n(emp.baseSalary);
  // Absent = recorded days (unchanged by Leave). Leave only affects pay via Present.
  const daysAbsent = d ? n(d.daysAbsent) : n(emp.daysAbsent);
  const daysPresent = d ? n(d.daysPresent) : n(emp.daysPresent);
  const leaveUsed = d ? n(d.leaveUsed) : n(emp.leaveUsed);
  const daysLate = d ? n(d.daysLate) : n(emp.daysLate);
  const daysHalfDay = d ? n(d.daysHalfDay) : n(emp.daysHalfDay);
  const allowance = d ? n(d.allowanceAmount) : n(emp.allowanceAmount);
  const bonus = d ? n(d.bonusAmount) : n(emp.bonusAmount);
  const loan = d ? n(d.loanDeductionAmount) : n(emp.loanDeductionAmount);
  const advance = d ? n(d.advanceAmount) : n(emp.advanceAmount);
  const perDay = monthDays ? base / monthDays : 0;
  const lateOffDays = Math.floor(daysLate / latesPerOff);
  const lateDed = round2(lateOffDays * perDay);
  const halfDed = round2(daysHalfDay * perDay * 0.5);
  const gross = round2(perDay * daysPresent + allowance + bonus);
  const taxComputed = monthlyTaxFromGross(gross, opts.slabs);
  const tax = d?.taxManual ? n(d.monthlyTax) : taxComputed;
  const net = Math.max(0, round2(gross - lateDed - loan - halfDed - advance - tax));
  return {
    employeeId: emp.employeeId,
    fullName: emp.fullName,
    roleTitle: emp.roleTitle,
    employeeCode: emp.employeeCode,
    leaveAllowance: emp.leaveAllowance,
    leaveUsed,
    base,
    perDay,
    daysPresent,
    daysAbsent,
    daysLate,
    daysHalfDay,
    lateOffDays,
    allowance,
    bonus,
    gross,
    lateDed,
    halfDed,
    loan,
    advance,
    taxComputed,
    tax,
    net,
    paymentMode: normalizePaymentMode(d?.paymentMode ?? emp.paymentMode),
    remarks: d?.remarks ?? emp.remarks ?? "",
    draft: d ?? draftFromEmployee(emp),
  };
}

export function draftFromEmployee(e: PayrollComputeRow): SheetDraft {
  return {
    baseSalary: String(e.baseSalary ?? ""),
    daysPresent: String(e.daysPresent ?? 0),
    daysAbsent: String(e.daysAbsent ?? 0),
    leaveUsed: String(e.leaveUsed ?? 0),
    daysLate: String(e.daysLate ?? 0),
    daysHalfDay: String(e.daysHalfDay ?? 0),
    allowanceAmount: String(e.allowanceAmount ?? 0),
    bonusAmount: String(e.bonusAmount ?? 0),
    loanDeductionAmount: String(e.loanDeductionAmount ?? 0),
    advanceAmount: String(e.advanceAmount ?? 0),
    monthlyTax: String(e.monthlyTax ?? 0),
    taxManual: Boolean(e.taxManual),
    paymentMode: normalizePaymentMode(e.paymentMode),
    remarks: e.remarks ?? "",
  };
}

export function draftFromResult(result: PayrollComputeResult): Record<number, SheetDraft> {
  const next: Record<number, SheetDraft> = {};
  for (const e of result.employees) {
    next[e.employeeId] = draftFromEmployee(e);
  }
  return next;
}

export function applyAttendancePatch(
  current: SheetDraft,
  patch: Partial<SheetDraft>,
  monthDays: number,
  latesPerOff = 3,
): Partial<SheetDraft> {
  const next = { ...patch };
  const days = monthDays || 30;

  // Leave forgives pay only: +1 leave → +1 present, Absent stays as recorded no-shows.
  if (patch.leaveUsed != null && patch.daysAbsent == null) {
    const prevLeave = n(current.leaveUsed);
    const absent = n(current.daysAbsent);
    const requested = Math.max(0, n(patch.leaveUsed));
    const leave = Math.min(requested, absent);
    next.leaveUsed = String(leave);
    if (patch.daysPresent == null) {
      const delta = leave - prevLeave;
      next.daysPresent = String(Math.max(0, n(current.daysPresent) + delta));
    }
  }

  // Late Coming changes Late Absents (floor(lates / 3)) for pay — never touches Absent.
  // Absent edits: keep Leave as forgiveness; Present = month − chargeable (Absent − Leave).
  if (patch.daysAbsent != null && patch.daysPresent == null) {
    const absent = Math.max(0, n(patch.daysAbsent));
    const leave = Math.min(n(next.leaveUsed ?? current.leaveUsed), absent);
    next.leaveUsed = String(leave);
    next.daysPresent = String(Math.max(0, days - Math.max(0, absent - leave)));
  }

  // Manual Present edits stand alone — do not rewrite recorded Absent or Leave.
  // Late Coming edits stand alone — Late Absents / Late Deduction derive from the count.

  const calcInputs = [
    "baseSalary",
    "daysPresent",
    "daysAbsent",
    "leaveUsed",
    "daysLate",
    "daysHalfDay",
    "allowanceAmount",
    "bonusAmount",
  ];
  if (calcInputs.some((k) => k in patch || k in next)) {
    next.taxManual = false;
  }
  return next;
}

export function slabsFromResult(result: PayrollComputeResult): TaxSlabInput[] {
  return (result.taxSlabs ?? []).map((s) => ({
    sortOrder: s.sortOrder,
    minAmount: n(s.minAmount),
    maxAmount: s.maxAmount == null ? null : n(s.maxAmount),
    fixedAmount: n(s.fixedAmount),
    ratePercent: n(s.ratePercent),
    excessOver: n(s.excessOver),
  }));
}
