import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import {
  useEmployeeDevelopmentEmployees,
  useEmployeeDevelopmentSelection,
} from "../../hooks/useEmployeeDevelopmentEmployees";
import {
  useEmployeePerformance,
  useEmployeePerformanceAiSummary,
} from "../../hooks/useEmployeePerformance";

const selectStyle: CSSProperties = {
  minWidth: 200,
  padding: "var(--space-2) var(--space-3)",
  border: "1px solid var(--color-border-strong)",
  borderRadius: "var(--radius-sm)",
  background: "var(--color-surface)",
  fontFamily: "var(--font-ui)",
  fontSize: "var(--text-sm)",
  color: "var(--color-text-primary)",
};

function scoreBand(score: number): "on_target" | "at_risk" | "below_target" {
  if (score >= 9) return "on_target";
  if (score >= 7) return "at_risk";
  return "below_target";
}

function moneyOrNum(n: string | number | null | undefined): string {
  if (n == null || n === "") return "—";
  return Number(n).toLocaleString("en-PK", { maximumFractionDigits: 2 });
}

function formatNum(n: string | number | null | undefined, digits = 1): string {
  if (n == null || n === "") return "—";
  return Number(n).toFixed(digits);
}

export function EmployeePerformancePage() {
  const { hasPermission } = useAuth();
  const { selfService, linkedEmployeeId, canListEmployees, employees } =
    useEmployeeDevelopmentEmployees();
  const canWrite = hasPermission("kpi", "write");
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const { employeeId, setEmployeeId } = useEmployeeDevelopmentSelection(
    Boolean(employees.data?.items.length),
    employees.data?.items,
    { selfService, linkedEmployeeId },
  );
  const [error, setError] = useState<string | null>(null);
  const [aiText, setAiText] = useState<string | null>(null);

  const queryParams = useMemo(() => {
    if (employeeId === "") return null;
    return {
      employeeId: Number(employeeId),
      periodYear: year,
      periodMonth: month,
    };
  }, [employeeId, year, month]);

  const performance = useEmployeePerformance(queryParams);
  const aiMutation = useEmployeePerformanceAiSummary();
  const data = performance.data;
  const showPerformanceLoading = performance.isFetching && !data;

  useEffect(() => {
    setAiText(performance.data?.aiSummary ?? null);
    setError(null);
  }, [performance.data]);

  async function onGenerateAi() {
    if (!queryParams) return;
    setError(null);
    try {
      const res = await aiMutation.mutateAsync(queryParams);
      setAiText(res.aiSummary);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate AI summary");
    }
  }

  const employeeOptions = employees.data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Employee Performance"
        breadcrumb="Employee Development / Employee Performance"
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <Card>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Select an employee and month to review logged KPIs. The score out of 10 updates as KPIs
            are logged; past months are saved when the month ends.
          </p>
          <div
            style={{
              display: "grid",
              gap: "var(--space-3)",
              gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
              maxWidth: 900,
            }}
          >
            <label className="form-field">
              <span className="form-field__label">Employee</span>
              <select
                className="form-field__input"
                style={selectStyle}
                value={employeeId === "" ? "" : String(employeeId)}
                disabled={selfService}
                onChange={(e) => setEmployeeId(e.target.value ? Number(e.target.value) : "")}
              >
                {!selfService ? <option value="">Select employee…</option> : null}
                {selfService && linkedEmployeeId ? (
                  <option value={linkedEmployeeId}>
                    {data?.employeeName ?? `Employee #${linkedEmployeeId}`}
                  </option>
                ) : employees.isLoading ? (
                  <option value="" disabled>
                    Loading employees…
                  </option>
                ) : employees.isError ? (
                  <option value="" disabled>
                    Could not load employees
                  </option>
                ) : !canListEmployees ? (
                  <option value="" disabled>
                    Employees list requires employees read access
                  </option>
                ) : (
                  employeeOptions.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.fullName} ({e.employeeCode})
                    </option>
                  ))
                )}
              </select>
              {!selfService && employees.isError ? (
                <span className="form-field__error">
                  {employees.error instanceof ApiError
                    ? employees.error.message
                    : "Could not load the employee list."}
                </span>
              ) : null}
            </label>
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
          </div>
          {error ? (
            <p style={{ color: "var(--color-status-critical)", marginBottom: 0 }}>{error}</p>
          ) : null}
        </Card>

        {employeeId === "" ? (
          <EmptyState
            title="Select an employee"
            description="Choose someone from the dropdown to see their KPI performance for the month."
          />
        ) : null}

        {showPerformanceLoading ? <Spinner label="Loading performance" /> : null}
        {performance.isError && !data ? (
          <EmptyState
            title="Could not load performance"
            description={
              performance.error instanceof ApiError
                ? performance.error.message
                : "Please try again."
            }
          />
        ) : null}

        {data ? (
          <>
            {performance.isFetching ? (
              <p
                style={{
                  margin: 0,
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-muted)",
                }}
              >
                Updating performance…
              </p>
            ) : null}
            <section
              style={{
                display: "grid",
                gap: "var(--space-4)",
                gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))",
              }}
            >
              <Card status={scoreBand(Number(data.scoreOutOf10))}>
                <div
                  style={{
                    fontSize: "var(--text-xs)",
                    color: "var(--color-text-secondary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.02em",
                    fontWeight: "var(--weight-semibold)",
                  }}
                >
                  {data.periodLabel} score
                </div>
                <div
                  className="font-data"
                  style={{ fontSize: "var(--text-2xl)", marginTop: "var(--space-2)" }}
                >
                  {formatNum(data.scoreOutOf10, 1)}
                  <span style={{ fontSize: "var(--text-lg)", color: "var(--color-text-muted)" }}>
                    {" "}
                    / 10
                  </span>
                </div>
                <p
                  style={{
                    margin: "var(--space-2) 0 0",
                    fontSize: "var(--text-sm)",
                    color: "var(--color-text-muted)",
                  }}
                >
                  {data.isFinalized
                    ? "Saved month score"
                    : data.isCurrentMonth
                      ? "Live score — updates as KPIs are logged"
                      : "Computed from logged KPIs"}
                  {data.overallPct != null
                    ? ` · ${formatNum(data.overallPct, 1)}% achievement`
                    : ""}
                </p>
              </Card>
              <Card>
                <div
                  style={{
                    fontSize: "var(--text-xs)",
                    color: "var(--color-text-secondary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.02em",
                    fontWeight: "var(--weight-semibold)",
                  }}
                >
                  KPI entries this month
                </div>
                <div
                  className="font-data"
                  style={{ fontSize: "var(--text-2xl)", marginTop: "var(--space-2)" }}
                >
                  {data.entriesCount}
                </div>
                <p
                  style={{
                    margin: "var(--space-2) 0 0",
                    fontSize: "var(--text-sm)",
                    color: "var(--color-text-muted)",
                  }}
                >
                  {data.employeeName} · {data.employeeCode}
                </p>
              </Card>
            </section>

            {data.history.length > 0 ? (
              <Card>
                <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Saved monthly scores</h2>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                  {data.history.map((h) => (
                    <button
                      key={`${h.periodYear}-${h.periodMonth}`}
                      type="button"
                      onClick={() => {
                        setYear(h.periodYear);
                        setMonth(h.periodMonth);
                      }}
                      style={{
                        border: "1px solid var(--color-border)",
                        borderLeft: "3px solid var(--color-accent)",
                        borderRadius: "var(--radius-md)",
                        background: "var(--color-surface-alt)",
                        padding: "var(--space-2) var(--space-3)",
                        cursor: "pointer",
                        fontFamily: "var(--font-ui)",
                        fontSize: "var(--text-sm)",
                        color: "var(--color-text-primary)",
                      }}
                    >
                      {h.label} ={" "}
                      <span className="font-data">{formatNum(h.scoreOutOf10, 1)}/10</span>
                    </button>
                  ))}
                </div>
              </Card>
            ) : null}

            <Card>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  flexWrap: "wrap",
                  marginBottom: "var(--space-3)",
                }}
              >
                <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>AI performance summary</h2>
                {canWrite ? (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={aiMutation.isPending || data.entriesCount === 0}
                    onClick={() => void onGenerateAi()}
                  >
                    {aiMutation.isPending ? "Generating…" : "Generate AI summary"}
                  </Button>
                ) : null}
              </div>
              {aiText ? (
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    fontFamily: "var(--font-ui)",
                    fontSize: "var(--text-sm)",
                    lineHeight: 1.55,
                    color: "var(--color-text-primary)",
                  }}
                >
                  {aiText}
                </pre>
              ) : (
                <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                  {data.entriesCount === 0
                    ? "No KPIs logged this month yet — summary will be available after entries exist."
                    : "No AI summary yet. Generate one to get a coaching-style review of this month."}
                </p>
              )}
            </Card>

            <section>
              <h2 style={{ margin: "0 0 var(--space-3)", fontSize: "var(--text-lg)" }}>
                Logged KPIs — {data.periodLabel}
              </h2>
              {data.entries.length === 0 ? (
                <EmptyState
                  title="No KPIs logged"
                  description="KPI entries for this employee in this month will appear here once they are submitted from the KPI dashboard."
                />
              ) : (
                <Table
                  headers={[
                    "KPI",
                    "Period",
                    "Actual",
                    "Target",
                    "Weight",
                    "Score %",
                    "Notes",
                  ]}
                >
                  {data.entries.map((row) => (
                    <tr
                      key={row.id}
                      data-status={
                        row.score == null
                          ? "neutral"
                          : row.score >= 90
                            ? "positive"
                            : row.score >= 70
                              ? "warning"
                              : "critical"
                      }
                    >
                      <td>{row.kpiName}</td>
                      <td className="font-data" style={{ fontSize: "var(--text-xs)" }}>
                        {row.periodStart} → {row.periodEnd}
                      </td>
                      <td className="num">{moneyOrNum(row.actualValue)}</td>
                      <td className="num">{moneyOrNum(row.targetValue)}</td>
                      <td className="num">
                        {row.weight != null ? formatNum(row.weight, 2) : "—"}
                      </td>
                      <td>
                        {row.score != null ? (
                          <StatusBadge
                            status={
                              row.score >= 90
                                ? "approved"
                                : row.score >= 70
                                  ? "pending"
                                  : "rejected"
                            }
                          >
                            {formatNum(row.score, 1)}%
                          </StatusBadge>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td style={{ maxWidth: 280 }}>{row.notes || "—"}</td>
                    </tr>
                  ))}
                </Table>
              )}
            </section>
          </>
        ) : null}
      </div>
    </>
  );
}
