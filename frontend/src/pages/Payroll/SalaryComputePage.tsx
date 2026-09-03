import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { SalarySheet, draftFromResult, type SheetDraft } from "../../components/domain/SalarySheet";
import { normalizePaymentMode } from "../../lib/salarySheet";
import { usePayrollCompute, usePayrollAiSummary, useSavePayrollSheet, useTaxYears } from "../../hooks/usePayroll";
import { useAuth } from "../../hooks/useAuth";
import { downloadSalarySheetExcel } from "../../api/payroll";
import { ApiError } from "../../api/client";
import type { PayrollAiSummary, PayrollComputeResult } from "../../types/payroll";

export function SalaryComputePage() {
  const { hasPermission } = useAuth();
  const canEdit = hasPermission("payroll", "write");
  const [searchParams] = useSearchParams();
  const now = new Date();
  const paramMonth = Number(searchParams.get("month"));
  const paramYear = Number(searchParams.get("year"));
  const [month, setMonth] = useState(
    paramMonth >= 1 && paramMonth <= 12 ? paramMonth : now.getMonth() + 1,
  );
  const [year, setYear] = useState(
    paramYear >= 2000 && paramYear <= 2100 ? paramYear : now.getFullYear(),
  );
  const taxYears = useTaxYears();
  const [taxYearId, setTaxYearId] = useState<number | "">("");
  const [drafts, setDrafts] = useState<Record<number, SheetDraft>>({});
  const [removedIds, setRemovedIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [aiSummary, setAiSummary] = useState<PayrollAiSummary | null>(null);
  const saveSheet = useSavePayrollSheet();
  const aiSummaryMutation = usePayrollAiSummary();

  useEffect(() => {
    if (paramMonth >= 1 && paramMonth <= 12) setMonth(paramMonth);
    if (paramYear >= 2000 && paramYear <= 2100) setYear(paramYear);
  }, [paramMonth, paramYear]);

  const activeTaxId = useMemo(() => {
    if (taxYearId !== "") return taxYearId;
    const active = (taxYears.data ?? []).find((y) => y.isActive) ?? taxYears.data?.[0];
    return active?.id ?? "";
  }, [taxYearId, taxYears.data]);

  const compute = usePayrollCompute(
    activeTaxId === ""
      ? null
      : { periodMonth: month, periodYear: year, taxYearId: Number(activeTaxId) },
  );

  useEffect(() => {
    if (compute.data) {
      setDrafts(draftFromResult(compute.data));
      setRemovedIds([]);
    }
  }, [compute.data]);

  useEffect(() => {
    setAiSummary(null);
  }, [month, year]);

  const displayResult: PayrollComputeResult | null = useMemo(() => {
    if (!compute.data) return null;
    if (removedIds.length === 0) return compute.data;
    const removed = new Set(removedIds);
    return {
      ...compute.data,
      employees: compute.data.employees.filter((e) => !removed.has(e.employeeId)),
    };
  }, [compute.data, removedIds]);

  function patchDraft(employeeId: number, patch: Partial<SheetDraft>) {
    setDrafts((prev) => ({
      ...prev,
      [employeeId]: { ...prev[employeeId], ...patch } as SheetDraft,
    }));
    setMessage(null);
  }

  function deleteRow(employeeId: number, fullName: string) {
    const ok = window.confirm(
      `Remove ${fullName} from this month's salary sheet?\n\nSave the sheet to keep them removed. A professional attendance import for this month can bring them back.`,
    );
    if (!ok) return;
    setRemovedIds((prev) => (prev.includes(employeeId) ? prev : [...prev, employeeId]));
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[employeeId];
      return next;
    });
    setMessage(`${fullName} removed from this sheet — save to keep the change.`);
    setError(null);
  }

  async function save() {
    if (!compute.data) return;
    setError(null);
    setMessage(null);
    const removed = new Set(removedIds);
    try {
      const keptItems = compute.data.employees
        .filter((e) => !removed.has(e.employeeId))
        .map((e) => {
          const d = drafts[e.employeeId];
          const live = {
            baseSalary: Number(d?.baseSalary ?? e.baseSalary),
            daysPresent: Number(d?.daysPresent ?? e.daysPresent),
            daysAbsent: Number(d?.daysAbsent ?? e.daysAbsent),
            leaveUsed: Number(d?.leaveUsed ?? e.leaveUsed ?? 0),
            daysLate: Number(d?.daysLate ?? e.daysLate),
            daysHalfDay: Number(d?.daysHalfDay ?? e.daysHalfDay),
            allowanceAmount: Number(d?.allowanceAmount ?? e.allowanceAmount ?? 0),
            bonusAmount: Number(d?.bonusAmount ?? e.bonusAmount ?? 0),
            loanDeductionAmount: Number(d?.loanDeductionAmount ?? e.loanDeductionAmount ?? 0),
            advanceAmount: Number(d?.advanceAmount ?? e.advanceAmount ?? 0),
            paymentMode: normalizePaymentMode(d?.paymentMode ?? e.paymentMode),
            remarks: d?.remarks || null,
            monthlyTaxOverride: d?.taxManual ? Number(d.monthlyTax) : null,
            excluded: false,
          };
          return {
            employeeId: e.employeeId,
            ...live,
            baseSalary: Number.isFinite(live.baseSalary) ? live.baseSalary : Number(e.baseSalary),
          };
        });
      const removedItems = compute.data.employees
        .filter((e) => removed.has(e.employeeId))
        .map((e) => ({
          employeeId: e.employeeId,
          allowanceAmount: 0,
          bonusAmount: 0,
          loanDeductionAmount: 0,
          advanceAmount: 0,
          paymentMode: normalizePaymentMode(e.paymentMode),
          remarks: e.remarks || null,
          excluded: true,
        }));
      await saveSheet.mutateAsync({
        periodMonth: month,
        periodYear: year,
        items: [...keptItems, ...removedItems],
      });
      setMessage(
        removedItems.length
          ? `Salary sheet saved (${removedItems.length} row${removedItems.length === 1 ? "" : "s"} removed)`
          : "Salary sheet saved",
      );
      setRemovedIds([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    }
  }

  async function downloadExcel() {
    if (activeTaxId === "") return;
    setError(null);
    try {
      const blob = await downloadSalarySheetExcel({
        periodMonth: month,
        periodYear: year,
        taxYearId: Number(activeTaxId),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Salary_Sheet_${year}-${String(month).padStart(2, "0")}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  }

  async function generateAiSummary() {
    if (activeTaxId === "") return;
    setError(null);
    try {
      const summary = await aiSummaryMutation.mutateAsync({
        periodMonth: month,
        periodYear: year,
        taxYearId: Number(activeTaxId),
      });
      setAiSummary(summary);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI summary failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Salary calculation"
        breadcrumb="Payroll / Salary calculation"
        actions={
          <>
            {canEdit ? (
              <Button variant="primary" disabled={!compute.data || saveSheet.isPending} onClick={save}>
                {saveSheet.isPending ? "Saving…" : "Save salary sheet"}
              </Button>
            ) : null}
            <Button variant="secondary" disabled={!compute.data} onClick={downloadExcel}>
              Download Excel
            </Button>
            <Button
              variant="secondary"
              disabled={!compute.data || aiSummaryMutation.isPending || activeTaxId === ""}
              onClick={() => void generateAiSummary()}
            >
              {aiSummaryMutation.isPending ? "Generating summary…" : "Generate AI summary"}
            </Button>
            <Link to="/payroll/tax-slabs">
              <Button variant="secondary">Tax slabs</Button>
            </Link>
            <Link to="/attendance/period-report">
              <Button variant="secondary">Import Excel file for attendance</Button>
            </Link>
          </>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <Card>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Edit this sheet like Excel. Changing base salary, leave, absents, lates, or half-days
            immediately recalculates per-day rate, late offs (3 lates = 1 absent day), half-day
            deduction, tax, and net payable. Leave forgives pay only — +1 Leave raises Present / net
            but does not change the Absent column. Use the trash icon to remove a row from this
            month&apos;s sheet, then Save. Full screen expands the editor. Present and absent stay
            on a 30-day month.
          </p>
          <div
            style={{
              display: "grid",
              gap: "var(--space-3)",
              gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
              maxWidth: 720,
            }}
          >
            <label className="form-field">
              <span className="form-field__label">Month</span>
              <select
                className="form-field__input"
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
              >
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {new Date(2000, i, 1).toLocaleString("en", { month: "long" })}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span className="form-field__label">Year</span>
              <input
                className="form-field__input font-data"
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              />
            </label>
            <label className="form-field">
              <span className="form-field__label">Tax year</span>
              <select
                className="form-field__input"
                value={activeTaxId === "" ? "" : String(activeTaxId)}
                onChange={(e) => setTaxYearId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Select…</option>
                {(taxYears.data ?? []).map((y) => (
                  <option key={y.id} value={y.id}>
                    {y.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {error ? (
            <p style={{ color: "var(--color-status-critical)", marginBottom: 0 }}>{error}</p>
          ) : null}
          {message ? (
            <p style={{ color: "var(--color-status-positive)", marginBottom: 0 }}>{message}</p>
          ) : null}
        </Card>

        {compute.isLoading ? <Spinner label="Calculating salaries" /> : null}
        {compute.isError ? (
          <p style={{ color: "var(--color-status-critical)" }}>Could not compute payroll.</p>
        ) : null}

        {displayResult ? (
          <SalarySheet
            result={displayResult}
            drafts={drafts}
            canEdit={canEdit}
            onDraftChange={patchDraft}
            onDeleteRow={canEdit ? deleteRow : undefined}
            aiSummary={aiSummary ?? displayResult.aiSummary}
          />
        ) : null}
      </div>
    </>
  );
}
