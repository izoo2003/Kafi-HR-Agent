import { useEffect, useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import type { PayrollAiSummary, PayrollComputeResult } from "../../types/payroll";
import {
  applyAttendancePatch,
  computeLiveRow,
  normalizePaymentMode,
  SALARY_PAYMENT_MODES,
  slabsFromResult,
  type SheetDraft,
} from "../../lib/salarySheet";
import "./SalarySheet.css";

export type { SheetDraft } from "../../lib/salarySheet";
export { draftFromResult } from "../../lib/salarySheet";

function money(n: string | number | null | undefined): string {
  if (n == null || n === "") return "—";
  return Number(n).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function monthTitle(month: number, year: number): string {
  const label = new Date(2000, month - 1, 1).toLocaleString("en", { month: "long" }).toUpperCase();
  return `${label}-${year}`;
}

type Props = {
  result: PayrollComputeResult;
  drafts: Record<number, SheetDraft>;
  canEdit: boolean;
  onDraftChange: (employeeId: number, patch: Partial<SheetDraft>) => void;
  aiSummary?: PayrollAiSummary | null;
};

function NumInput({
  value,
  onChange,
  label,
  step = "1",
}: {
  value: string;
  onChange: (v: string) => void;
  label: string;
  step?: string;
}) {
  return (
    <input
      className="salary-sheet__input"
      type="number"
      min={0}
      step={step}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
    />
  );
}

export function SalarySheet({ result, drafts, canEdit, onDraftChange, aiSummary }: Props) {
  const [fullscreen, setFullscreen] = useState(false);
  const monthDays = result.monthDays || 30;
  const latesPerOff = result.latesPerOff || 3;
  const slabs = slabsFromResult(result);
  const rows = result.employees.map((e) =>
    computeLiveRow(e, drafts[e.employeeId], { monthDays, latesPerOff, slabs }),
  );
  const summary = aiSummary ?? result.aiSummary ?? null;

  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setFullscreen(false);
    };
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [fullscreen]);

  const totals = rows.reduce(
    (acc, r) => {
      acc.base += r.base;
      acc.allowance += r.allowance;
      acc.bonus += r.bonus;
      acc.gross += r.gross;
      acc.lateDed += r.lateDed;
      acc.halfDed += r.halfDed;
      acc.loan += r.loan;
      acc.advance += r.advance;
      acc.tax += r.tax;
      acc.net += r.net;
      return acc;
    },
    {
      base: 0,
      allowance: 0,
      bonus: 0,
      gross: 0,
      lateDed: 0,
      halfDed: 0,
      loan: 0,
      advance: 0,
      tax: 0,
      net: 0,
    },
  );

  function edit(employeeId: number, current: SheetDraft, patch: Partial<SheetDraft>) {
    onDraftChange(employeeId, applyAttendancePatch(current, patch, monthDays, latesPerOff));
  }

  const sheet = (
    <div className="salary-sheet-wrap">
      <div className="salary-sheet__toolbar">
        <button
          type="button"
          className="salary-sheet__fullscreen-btn"
          onClick={() => setFullscreen((value) => !value)}
          aria-pressed={fullscreen}
          title={fullscreen ? "Exit full screen (Esc)" : "Full screen salary sheet"}
        >
          {fullscreen ? <Minimize2 size={16} aria-hidden /> : <Maximize2 size={16} aria-hidden />}
          <span>{fullscreen ? "Exit full screen" : "Full screen"}</span>
        </button>
      </div>
      <div className="salary-sheet__scroll">
        <table className="salary-sheet">
          <colgroup>
            <col style={{ width: 48 }} />
            <col style={{ width: 160 }} />
            <col style={{ width: 140 }} />
            <col style={{ width: 100 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 56 }} />
            <col style={{ width: 56 }} />
            <col style={{ width: 56 }} />
            <col style={{ width: 56 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 100 }} />
            <col style={{ width: 70 }} />
            <col style={{ width: 110 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 110 }} />
            <col style={{ width: 90 }} />
            <col style={{ width: 110 }} />
            <col style={{ width: 100 }} />
            <col style={{ width: 110 }} />
            <col style={{ width: 160 }} />
          </colgroup>
          <thead>
            <tr>
              <th className="salary-sheet__company" colSpan={21}>
                {result.companyName || "KAFI COMMODITIES (PVT) LTD"}
              </th>
            </tr>
            <tr>
              <th className="salary-sheet__month" colSpan={21}>
                Salary Sheet For The Month Of {monthTitle(result.periodMonth, result.periodYear)}
              </th>
            </tr>
            <tr>
              <th className="salary-sheet__group" colSpan={3}>
                Employee&apos;s Detail
              </th>
              <th className="salary-sheet__group">Salary</th>
              <th className="salary-sheet__group">Per Day</th>
              <th className="salary-sheet__group" colSpan={3}>
                Attendance
              </th>
              <th className="salary-sheet__group">Half Day</th>
              <th className="salary-sheet__group">Allowance</th>
              <th className="salary-sheet__group">Bonus</th>
              <th className="salary-sheet__group">Gross</th>
              <th className="salary-sheet__group">Late Coming</th>
              <th className="salary-sheet__group">Late Deduction</th>
              <th className="salary-sheet__group">Half Deduction</th>
              <th className="salary-sheet__group">Loan Deduction</th>
              <th className="salary-sheet__group">Advance</th>
              <th className="salary-sheet__group">Tax/Other</th>
              <th className="salary-sheet__group">Net Payable</th>
              <th className="salary-sheet__group">Mode of Payment</th>
              <th className="salary-sheet__group">Remarks</th>
            </tr>
            <tr>
              <th className="salary-sheet__sub">S.No#</th>
              <th className="salary-sheet__sub">Name</th>
              <th className="salary-sheet__sub">Designation</th>
              <th className="salary-sheet__sub" />
              <th className="salary-sheet__sub">Salary</th>
              <th className="salary-sheet__sub">P</th>
              <th className="salary-sheet__sub">A</th>
              <th className="salary-sheet__sub" title="Paid leave days — each leave reduces absent by 1">
                Leave
              </th>
              <th className="salary-sheet__sub">Days</th>
              <th className="salary-sheet__sub">Amount</th>
              <th className="salary-sheet__sub">Amount</th>
              <th className="salary-sheet__sub">Salary</th>
              <th className="salary-sheet__sub">Count</th>
              <th className="salary-sheet__sub">Amount</th>
              <th className="salary-sheet__sub">Amount</th>
              <th className="salary-sheet__sub" />
              <th className="salary-sheet__sub" />
              <th className="salary-sheet__sub" />
              <th className="salary-sheet__sub" />
              <th className="salary-sheet__sub" />
              <th className="salary-sheet__sub" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.employeeId} data-status="positive">
                <td className="ctr">{i + 1}</td>
                <td className="salary-sheet__name">
                  <div>{r.fullName}</div>
                  {r.lateOffDays > 0 ? (
                    <div className="salary-sheet__hint">
                      {r.daysLate} lates → {r.lateOffDays} off
                    </div>
                  ) : null}
                  {r.leaveAllowance > 0 ? (
                    <div className="salary-sheet__hint salary-sheet__hint--muted">
                      Leave allowance {r.leaveAllowance}
                    </div>
                  ) : null}
                </td>
                <td>{r.roleTitle}</td>
                <td>
                  {canEdit ? (
                    <NumInput
                      step="0.01"
                      value={r.draft.baseSalary}
                      label={`Salary for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { baseSalary: v })}
                    />
                  ) : (
                    <span className="num">{money(r.base)}</span>
                  )}
                </td>
                <td className="num salary-sheet__formula">{money(r.perDay)}</td>
                <td>
                  {canEdit ? (
                    <NumInput
                      value={r.draft.daysPresent}
                      label={`Present days for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { daysPresent: v })}
                    />
                  ) : (
                    <span className="ctr">{r.daysPresent}</span>
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <NumInput
                      value={r.draft.daysAbsent}
                      label={`Absent days for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { daysAbsent: v })}
                    />
                  ) : (
                    <span className="ctr">{r.daysAbsent}</span>
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <NumInput
                      value={r.draft.leaveUsed}
                      label={`Leave days for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { leaveUsed: v })}
                    />
                  ) : (
                    <span className="ctr">{r.leaveUsed}</span>
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <NumInput
                      value={r.draft.daysHalfDay}
                      label={`Half days for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { daysHalfDay: v })}
                    />
                  ) : (
                    <span className="ctr">{r.daysHalfDay}</span>
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <NumInput
                      step="0.01"
                      value={r.draft.allowanceAmount}
                      label={`Allowance for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { allowanceAmount: v })}
                    />
                  ) : (
                    <span className="num">{money(r.allowance)}</span>
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <NumInput
                      step="0.01"
                      value={r.draft.bonusAmount}
                      label={`Bonus for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { bonusAmount: v })}
                    />
                  ) : (
                    <span className="num">{money(r.bonus)}</span>
                  )}
                </td>
                <td className="num salary-sheet__formula">{money(r.gross)}</td>
                <td>
                  {canEdit ? (
                    <NumInput
                      value={r.draft.daysLate}
                      label={`Late count for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { daysLate: v })}
                    />
                  ) : (
                    <span className="ctr">{r.daysLate}</span>
                  )}
                </td>
                <td className="num salary-sheet__formula">{money(r.lateDed)}</td>
                <td className="num salary-sheet__formula">{money(r.halfDed)}</td>
                <td>
                  {canEdit ? (
                    <NumInput
                      step="0.01"
                      value={r.draft.loanDeductionAmount}
                      label={`Loan deduction for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { loanDeductionAmount: v })}
                    />
                  ) : (
                    <span className="num">{money(r.loan)}</span>
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <NumInput
                      step="0.01"
                      value={r.draft.advanceAmount}
                      label={`Advance for ${r.fullName}`}
                      onChange={(v) => edit(r.employeeId, r.draft, { advanceAmount: v })}
                    />
                  ) : (
                    <span className="num">{money(r.advance)}</span>
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <NumInput
                      step="0.01"
                      value={r.draft.taxManual ? r.draft.monthlyTax : String(r.taxComputed)}
                      label={`Tax for ${r.fullName}`}
                      onChange={(v) =>
                        edit(r.employeeId, r.draft, { monthlyTax: v, taxManual: true })
                      }
                    />
                  ) : (
                    <span className="num">{money(r.tax)}</span>
                  )}
                </td>
                <td className="num salary-sheet__net">{money(r.net)}</td>
                <td>
                  {canEdit ? (
                    <select
                      className="salary-sheet__input salary-sheet__input--text salary-sheet__select"
                      value={normalizePaymentMode(r.paymentMode)}
                      onChange={(ev) =>
                        edit(r.employeeId, r.draft, {
                          paymentMode: normalizePaymentMode(ev.target.value),
                        })
                      }
                      aria-label={`Payment mode for ${r.fullName}`}
                    >
                      {SALARY_PAYMENT_MODES.map((mode) => (
                        <option key={mode} value={mode}>
                          {mode}
                        </option>
                      ))}
                    </select>
                  ) : (
                    normalizePaymentMode(r.paymentMode)
                  )}
                </td>
                <td>
                  {canEdit ? (
                    <input
                      className="salary-sheet__input salary-sheet__input--text"
                      value={r.remarks}
                      onChange={(ev) => edit(r.employeeId, r.draft, { remarks: ev.target.value })}
                      aria-label={`Remarks for ${r.fullName}`}
                    />
                  ) : (
                    r.remarks
                  )}
                </td>
              </tr>
            ))}
            <tr className="salary-sheet__total">
              <td colSpan={3} style={{ textAlign: "right" }}>
                Grand Total
              </td>
              <td className="num">{money(totals.base)}</td>
              <td />
              <td />
              <td />
              <td />
              <td />
              <td className="num">{money(totals.allowance)}</td>
              <td className="num">{money(totals.bonus)}</td>
              <td className="num">{money(totals.gross)}</td>
              <td />
              <td className="num">{money(totals.lateDed)}</td>
              <td className="num">{money(totals.halfDed)}</td>
              <td className="num">{money(totals.loan)}</td>
              <td className="num">{money(totals.advance)}</td>
              <td className="num">{money(totals.tax)}</td>
              <td className="num salary-sheet__net">{money(totals.net)}</td>
              <td colSpan={2} />
            </tr>
            <tr className="salary-sheet__signoff">
              <td colSpan={6}>
                <div className="salary-sheet__signoff-line">Prepared By</div>
              </td>
              <td colSpan={8}>
                <div className="salary-sheet__signoff-line">Checked By</div>
              </td>
              <td colSpan={7}>
                <div className="salary-sheet__signoff-line">Approved By</div>
              </td>
            </tr>
            {summary?.summaryText ? (
              <tr className="salary-sheet__ai">
                <td colSpan={21}>
                  <h2 className="salary-sheet__ai-title">AI salary sheet summary</h2>
                  <p className="salary-sheet__ai-meta">
                    Payment modes — IBFT {summary.paymentModeCounts.IBFT ?? 0}, Cash{" "}
                    {summary.paymentModeCounts.Cash ?? 0}, Cheque {summary.paymentModeCounts.Cheque ?? 0}
                    {" · "}
                    {summary.employeeCount} employees · net{" "}
                    <span className="font-data">
                      {Number(summary.totalNetPayable).toLocaleString("en-PK", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </span>
                  </p>
                  <pre className="salary-sheet__ai-body">{summary.summaryText}</pre>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );

  if (fullscreen) {
    return (
      <div className="salary-sheet-fullscreen" role="dialog" aria-modal="true" aria-label="Salary sheet full screen">
        <div className="salary-sheet-fullscreen__panel">{sheet}</div>
      </div>
    );
  }

  return sheet;
}
