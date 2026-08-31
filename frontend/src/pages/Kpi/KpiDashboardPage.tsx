import { useMemo, useState, type FormEvent } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { ApiError } from "../../api/client";
import { KPI_STATUS_LABELS } from "../../constants/statusLabels";
import { useAuth } from "../../hooks/useAuth";
import { useDepartments } from "../../hooks/useEmployees";
import { isSelfService } from "../../lib/selfService";
import {
  useAiSuggestKpiEntry,
  useCreateKpiWorkSubmission,
  useDepartmentKpiSummary,
  useEmployeeKpiSummary,
  useGlobalKpiSummary,
  useKpiDailySummary,
  useKpiWorkLogs,
  useMarkKpiPeriodReviewed,
} from "../../hooks/useKpi";
import type { KpiBand, KpiWorkLog } from "../../types/kpi";

function monthRange(ym: string): { from: string; to: string } {
  const [y, m] = ym.split("-").map(Number);
  const from = `${y}-${String(m).padStart(2, "0")}-01`;
  const last = new Date(y, m, 0).getDate();
  const to = `${y}-${String(m).padStart(2, "0")}-${String(last).padStart(2, "0")}`;
  return { from, to };
}

function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function isSunday(iso: string): boolean {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).getDay() === 0;
}

function formatDay(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function ScoreTile({
  label,
  score,
  band,
  hint,
}: {
  label: string;
  score: number;
  band?: KpiBand;
  hint?: string;
}) {
  return (
    <Card status={band}>
      <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
        {score.toFixed(1)}
        <span style={{ fontSize: "var(--text-base)", color: "var(--color-text-muted)" }}> / 10</span>
      </div>
      <div>{label}</div>
      {hint ? (
        <div style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>{hint}</div>
      ) : null}
      {band ? (
        <StatusBadge status={band}>{KPI_STATUS_LABELS[band]}</StatusBadge>
      ) : null}
    </Card>
  );
}

function WorkLogList({ logs, showDepartment }: { logs: KpiWorkLog[]; showDepartment?: boolean }) {
  if (logs.length === 0) {
    return <p style={{ margin: 0, color: "var(--color-text-secondary)" }}>No work logged for this filter.</p>;
  }
  return (
    <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "var(--space-3)" }}>
      {logs.map((log, idx) => (
        <li
          key={`${log.id}-${idx}`}
          style={{
            borderLeft: "3px solid var(--color-accent)",
            paddingLeft: "var(--space-3)",
          }}
        >
          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <strong>{log.employeeName}</strong>
            {showDepartment ? (
              <span style={{ color: "var(--color-text-secondary)" }}>{log.departmentName}</span>
            ) : null}
            <span className="font-data" style={{ color: "var(--color-text-muted)" }}>
              {formatDay(log.workDate)} · {log.points.toFixed(1)} pts
            </span>
          </div>
          <p style={{ margin: "var(--space-1) 0 0" }}>{log.text}</p>
        </li>
      ))}
    </ul>
  );
}

export function KpiDashboardPage() {
  const { user, hasPermission } = useAuth();
  const selfService = isSelfService(user);
  const canWrite = hasPermission("kpi", "write");
  const canApprove = hasPermission("kpi", "approve") && !selfService;
  const departments = useDepartments();
  const now = new Date();
  const [month, setMonth] = useState(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`,
  );
  const [selectedDay, setSelectedDay] = useState("");
  const [departmentId, setDepartmentId] = useState<number | "">(
    selfService && user?.departmentId ? user.departmentId : "",
  );
  const monthBounds = useMemo(() => monthRange(month), [month]);
  const today = todayIso();
  const sundayToday = isSunday(today);
  const dayPickerMax = monthBounds.to < today ? monthBounds.to : today;
  const grain: "month" | "day" = selectedDay ? "day" : "month";
  const queryFrom = grain === "day" ? selectedDay : monthBounds.from;
  const queryTo = grain === "day" ? selectedDay : monthBounds.to;
  const deptId = departmentId === "" ? null : departmentId;
  const scopeAll = !selfService && deptId == null;

  const departmentName = useMemo(() => {
    const id = selfService ? user?.departmentId : deptId;
    if (!id) return "All departments";
    return (departments.data ?? []).find((d) => d.id === id)?.name ?? `Department #${id}`;
  }, [departments.data, deptId, selfService, user?.departmentId]);

  const empSummary = useEmployeeKpiSummary(
    selfService ? (user?.linkedEmployeeId ?? null) : null,
    monthBounds.from,
    monthBounds.to,
  );
  const summary = useDepartmentKpiSummary(selfService ? null : deptId, queryFrom, queryTo);
  const globalSummary = useGlobalKpiSummary(queryFrom, queryTo, !selfService && scopeAll);
  const dailySummary = useKpiDailySummary(
    monthBounds.from,
    monthBounds.to,
    selfService ? null : deptId,
    !selfService && grain === "month",
  );
  const workLogs = useKpiWorkLogs({
    periodStart: selfService ? monthBounds.from : queryFrom,
    periodEnd: selfService ? monthBounds.to : queryTo,
    departmentId: selfService ? user?.departmentId ?? null : deptId,
    employeeId: selfService ? user?.linkedEmployeeId ?? null : null,
    enabled: selfService || grain === "day" || deptId != null,
  });
  const createWorkSubmission = useCreateKpiWorkSubmission();
  const markReviewed = useMarkKpiPeriodReviewed();
  const aiSuggest = useAiSuggestKpiEntry();

  const [workDone, setWorkDone] = useState("");
  const [formattedWork, setFormattedWork] = useState<string | null>(null);
  const [pointsToAdd, setPointsToAdd] = useState<number | null>(null);
  const [effortLevel, setEffortLevel] = useState<
    "trivial" | "light" | "moderate" | "substantial" | "exceptional" | null
  >(null);
  const [effortScore, setEffortScore] = useState<number | null>(null);
  const [aiReasoning, setAiReasoning] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const workDays = dailySummary.data?.days ?? [];

  const logsByEmployee = useMemo(() => {
    const groups = new Map<number, { name: string; logs: KpiWorkLog[] }>();
    for (const log of workLogs.data ?? []) {
      const existing = groups.get(log.employeeId);
      if (existing) existing.logs.push(log);
      else groups.set(log.employeeId, { name: log.employeeName, logs: [log] });
    }
    return [...groups.values()];
  }, [workLogs.data]);

  function onMonthChange(value: string) {
    setMonth(value);
    const bounds = monthRange(value);
    if (selectedDay && (selectedDay < bounds.from || selectedDay > bounds.to)) {
      setSelectedDay("");
    }
  }

  async function onSaveWorkSubmission(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const text = (formattedWork ?? workDone).trim();
    if (!text) {
      setError("Describe the work done before saving.");
      return;
    }
    if (!formattedWork || pointsToAdd == null || !effortLevel) {
      setError("Analyze with AI first so effort and points are scored from your work notes.");
      return;
    }
    if (sundayToday) {
      setError("Sunday is not a workday — you can log again on Monday.");
      return;
    }
    try {
      await createWorkSubmission.mutateAsync({
        workDate: today,
        workText: workDone.trim(),
        formattedWork: formattedWork ?? undefined,
        pointsToAdd: pointsToAdd ?? undefined,
        effortLevel,
      });
      setWorkDone("");
      setFormattedWork(null);
      setPointsToAdd(null);
      setEffortLevel(null);
      setEffortScore(null);
      setAiReasoning(null);
      setMessage(`Work saved for ${formatDay(today)}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save work entry");
    }
  }

  async function onAiSuggest() {
    if (!workDone.trim()) {
      setError("Describe the work done before analyzing.");
      return;
    }
    setError(null);
    setAiReasoning(null);
    try {
      const res = await aiSuggest.mutateAsync({
        departmentId: Number(user?.departmentId),
        employeeId: Number(user?.linkedEmployeeId),
        periodStart: today,
        periodEnd: today,
        text: workDone.trim(),
      });
      setFormattedWork(res.formattedWork ?? workDone.trim());
      setPointsToAdd(res.pointsToAdd ?? 1);
      setEffortLevel(res.effortLevel ?? "light");
      setEffortScore(res.effortScore ?? null);
      setMessage("AI scored effort for this work — review below, then save.");
      setAiReasoning(res.reasoning);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI suggest failed");
    }
  }

  async function onMarkReviewed() {
    if (deptId == null) return;
    setError(null);
    setMessage(null);
    try {
      const res = await markReviewed.mutateAsync({
        departmentId: deptId,
        periodStart: monthBounds.from,
        periodEnd: monthBounds.to,
      });
      setMessage(res.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to mark period reviewed");
    }
  }

  const heading =
    grain === "day"
      ? scopeAll
        ? `Company ratings for ${formatDay(selectedDay)}`
        : `${departmentName} — ${formatDay(selectedDay)}`
      : scopeAll
        ? "Company daily ratings"
        : `${departmentName} — daily ratings`;

  return (
    <>
      <PageHeader
        title={selfService ? "My KPI dashboard" : "KPI Dashboard"}
        breadcrumb="KPI / Dashboard"
        actions={null}
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap", alignItems: "end" }}>
          <label className="form-field">
            <span className="form-field__label">Month</span>
            <input
              className="form-field__input"
              type="month"
              value={month}
              onChange={(e) => onMonthChange(e.target.value)}
            />
          </label>
          {selfService ? (
            <>
              <label className="form-field">
                <span className="form-field__label">Log date</span>
                <input className="form-field__input" value={formatDay(today)} readOnly disabled />
              </label>
              <label className="form-field">
                <span className="form-field__label">Department</span>
                <input className="form-field__input" value={departmentName} readOnly disabled />
              </label>
            </>
          ) : (
            <>
              <label className="form-field">
                <span className="form-field__label">Day (optional)</span>
                <input
                  className="form-field__input"
                  type="date"
                  min={monthBounds.from}
                  max={dayPickerMax}
                  value={selectedDay}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (!value) {
                      setSelectedDay("");
                      return;
                    }
                    if (isSunday(value)) {
                      setError("Sunday is not a workday — pick Monday through Saturday.");
                      return;
                    }
                    setError(null);
                    setSelectedDay(value);
                  }}
                />
              </label>
              <label className="form-field">
                <span className="form-field__label">Department</span>
                <select
                  className="form-field__input"
                  value={departmentId}
                  onChange={(e) => setDepartmentId(e.target.value ? Number(e.target.value) : "")}
                >
                  <option value="">All departments</option>
                  {(departments.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              {selectedDay ? (
                <Button type="button" variant="secondary" onClick={() => setSelectedDay("")}>
                  Clear day
                </Button>
              ) : null}
            </>
          )}
        </div>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
          {selfService
            ? "You can only log work for today (Monday–Saturday). Missed workdays count as 0; Sundays are excluded."
            : grain === "day" && scopeAll
              ? "Day + all departments: each department’s score for this day, plus every employee log. Employees who did not log count as 0."
              : grain === "day"
                ? "Day + department: every employee log in this department for this day. Missing logs count as 0."
                : scopeAll
                  ? "Month + all departments: each workday’s company score (Mon–Sat). Empty workdays are 0; Sundays are hidden. Pick a day or a department to see logs."
                  : "Month + department: each workday’s department score (empty = 0), plus every employee’s logs. People who did not log count as 0."}
        </p>

        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        {selfService ? (
          empSummary.isLoading ? (
            <Spinner label="Loading your KPIs" />
          ) : empSummary.data ? (
            <>
              <div
                style={{
                  display: "grid",
                  gap: "var(--space-3)",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                }}
              >
                <ScoreTile
                  label="Your contribution"
                  score={empSummary.data.contributionScore}
                  hint="Workdays this month, including 0s for days you skipped"
                />
                <ScoreTile
                  label="Department"
                  score={empSummary.data.departmentScore}
                  band={empSummary.data.departmentBand}
                />
                <ScoreTile
                  label="Company"
                  score={empSummary.data.globalScore}
                  band={empSummary.data.globalBand}
                />
                <Card>
                  <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                    {empSummary.data.submissionCount}
                  </div>
                  <div>Entries this month</div>
                </Card>
              </div>
              <section className="card">
                <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Your work log</h2>
                {workLogs.isLoading ? (
                  <Spinner label="Loading logs" />
                ) : (
                  <WorkLogList logs={workLogs.data ?? []} />
                )}
              </section>
            </>
          ) : (
            <EmptyState title="Ready to log work" description="Pick a date and describe what you did." />
          )
        ) : (
          <>
            {dailySummary.isLoading || globalSummary.isLoading || (deptId != null && summary.isLoading) ? (
              <Spinner label="Loading KPI summary" />
            ) : null}
            {dailySummary.isError || globalSummary.isError || summary.isError ? (
              <p style={{ color: "var(--color-status-critical)" }}>
                {dailySummary.error instanceof ApiError
                  ? dailySummary.error.message
                  : globalSummary.error instanceof ApiError
                    ? globalSummary.error.message
                    : summary.error instanceof ApiError
                      ? summary.error.message
                      : "Could not load KPI summary."}
              </p>
            ) : null}

            <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>{heading}</h2>
            <div
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              }}
            >
              {scopeAll && globalSummary.data ? (
                <ScoreTile
                  label={grain === "day" ? "Company this day" : "Company this month"}
                  score={globalSummary.data.overallScore}
                  band={globalSummary.data.band}
                  hint={
                    grain === "day"
                      ? "Average of departments that logged today"
                      : "Average of department scores"
                  }
                />
              ) : null}
              {deptId != null && summary.data ? (
                <ScoreTile
                  label={grain === "day" ? "Department this day" : "Department this month"}
                  score={summary.data.overallScore}
                  band={summary.data.band}
                  hint={`${summary.data.entriesRecorded}/${summary.data.entriesExpected} employees logged`}
                />
              ) : null}
              {dailySummary.data && grain === "month" ? (
                <ScoreTile
                  label={scopeAll ? "Avg daily company score" : "Avg daily department score"}
                  score={dailySummary.data.overallScore}
                  band={dailySummary.data.band}
                  hint={`${workDays.length} workdays (Sun omitted; empty = 0)`}
                />
              ) : null}
            </div>

            {grain === "month" ? (
              <section>
                <h3 style={{ fontSize: "var(--text-base)" }}>
                  {scopeAll ? "Each day’s company score" : "Each day’s department score"}
                </h3>
                {workDays.length === 0 ? (
                  <EmptyState
                    title="No workdays in this range yet"
                    description="Monday–Saturday through today appear here. Sundays are omitted. Empty workdays show as 0."
                  />
                ) : (
                  <Table headers={["Day", "Score", "Band", "People logged"]}>
                    {workDays.map((day) => (
                      <tr
                        key={day.date}
                        data-status={day.band}
                        style={{ cursor: "pointer" }}
                        onClick={() => setSelectedDay(day.date)}
                      >
                        <td>{formatDay(day.date)}</td>
                        <td className="font-data">{day.score.toFixed(1)} / 10</td>
                        <td>
                          <StatusBadge status={day.band}>{KPI_STATUS_LABELS[day.band]}</StatusBadge>
                        </td>
                        <td className="font-data">{day.entriesRecorded}</td>
                      </tr>
                    ))}
                  </Table>
                )}
              </section>
            ) : null}

            {scopeAll && globalSummary.data ? (
              <section>
                <h3 style={{ fontSize: "var(--text-base)" }}>
                  {grain === "day" ? "Department scores this day" : "Department ranking this month"}
                </h3>
                <Table headers={["Department", "Score", "Band", "Logged"]}>
                  {globalSummary.data.departments.map((dept) => (
                    <tr
                      key={dept.departmentId}
                      data-status={dept.band}
                      style={{ cursor: "pointer" }}
                      onClick={() => setDepartmentId(dept.departmentId)}
                    >
                      <td>{dept.departmentName}</td>
                      <td className="font-data">{dept.overallScore.toFixed(1)} / 10</td>
                      <td>
                        <StatusBadge status={dept.band}>{KPI_STATUS_LABELS[dept.band]}</StatusBadge>
                      </td>
                      <td className="font-data">
                        {dept.entriesRecorded}/{dept.entriesExpected}
                      </td>
                    </tr>
                  ))}
                </Table>
              </section>
            ) : null}

            {deptId != null && summary.data ? (
              <section>
                <h3 style={{ fontSize: "var(--text-base)" }}>Employee scores</h3>
                {summary.data.employees.length === 0 ? (
                  <EmptyState
                    title="No employees in this department"
                    description="Assign people to the department on the Employees page."
                  />
                ) : (
                  <Table headers={["Employee", "Score", "Band", "Entries"]}>
                    {summary.data.employees.map((emp) => (
                      <tr key={emp.employeeId} data-status={emp.band}>
                        <td>{emp.employeeName}</td>
                        <td className="font-data">{emp.contributionScore.toFixed(1)} / 10</td>
                        <td>
                          <StatusBadge status={emp.band}>{KPI_STATUS_LABELS[emp.band]}</StatusBadge>
                        </td>
                        <td className="font-data">{emp.submissionCount}</td>
                      </tr>
                    ))}
                  </Table>
                )}
              </section>
            ) : null}

            {(grain === "day" || deptId != null) && (
              <section className="card">
                <h3 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>
                  {grain === "day" && scopeAll
                    ? "All employee logs this day"
                    : grain === "day"
                      ? "Employee logs this day"
                      : "Employee logs this month"}
                </h3>
                {workLogs.isLoading ? (
                  <Spinner label="Loading logs" />
                ) : deptId != null && logsByEmployee.length > 0 ? (
                  <div style={{ display: "grid", gap: "var(--space-5)" }}>
                    {logsByEmployee.map((group) => (
                      <div key={group.name}>
                        <h4 style={{ margin: "0 0 var(--space-2)", fontSize: "var(--text-base)" }}>
                          {group.name}
                        </h4>
                        <WorkLogList logs={group.logs} showDepartment={scopeAll} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <WorkLogList logs={workLogs.data ?? []} showDepartment={scopeAll} />
                )}
              </section>
            )}

            {canApprove && deptId != null && grain === "month" ? (
              <div>
                <Button variant="primary" onClick={onMarkReviewed} disabled={markReviewed.isPending}>
                  Mark period reviewed
                </Button>
              </div>
            ) : null}
          </>
        )}

        {canWrite && selfService ? (
          sundayToday ? (
            <section className="card">
              <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Sunday is not a workday</h2>
              <p style={{ margin: 0, color: "var(--color-text-secondary)" }}>
                KPI logging is Monday through Saturday. You can log again tomorrow.
              </p>
            </section>
          ) : (
          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>
              Log work for today — {formatDay(today)}
            </h2>
            <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              Past and future dates cannot be logged.
            </p>
            <form onSubmit={onSaveWorkSubmission} style={{ display: "grid", gap: "var(--space-3)" }}>
              <label className="form-field">
                <span className="form-field__label">Work done</span>
                <textarea
                  className="form-field__input"
                  rows={5}
                  value={workDone}
                  onChange={(e) => {
                    setWorkDone(e.target.value);
                    setFormattedWork(null);
                    setPointsToAdd(null);
                    setEffortLevel(null);
                    setEffortScore(null);
                    setAiReasoning(null);
                  }}
                  placeholder="Describe what you accomplished this day…"
                  required
                />
              </label>
              {formattedWork ? (
                <div
                  className="card"
                  style={{ background: "var(--color-accent-subtle)", padding: "var(--space-3)" }}
                >
                  <strong>AI preview</strong>
                  <p style={{ margin: "var(--space-2) 0" }}>{formattedWork}</p>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "var(--space-2)",
                      alignItems: "center",
                      marginBottom: "var(--space-2)",
                    }}
                  >
                    {effortLevel ? (
                      <StatusBadge
                        status={
                          effortLevel === "exceptional" || effortLevel === "substantial"
                            ? "approved"
                            : effortLevel === "moderate"
                              ? "pending"
                              : "draft"
                        }
                      >
                        Effort: {effortLevel}
                        {effortScore != null ? ` (${effortScore}/5)` : ""}
                      </StatusBadge>
                    ) : null}
                    {pointsToAdd != null ? (
                      <span className="font-data" style={{ fontSize: "var(--text-sm)" }}>
                        +{pointsToAdd.toFixed(1)} pts today (max 10)
                      </span>
                    ) : null}
                  </div>
                  <p
                    style={{
                      margin: 0,
                      color: "var(--color-text-secondary)",
                      fontSize: "var(--text-sm)",
                    }}
                  >
                    Heavier workloads score more points than basic tasks. Day total still caps at 10.
                  </p>
                </div>
              ) : null}
              {aiReasoning ? (
                <p style={{ margin: 0, color: "var(--color-text-secondary)" }}>AI: {aiReasoning}</p>
              ) : null}
              <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={aiSuggest.isPending || !workDone.trim()}
                  onClick={onAiSuggest}
                >
                  {aiSuggest.isPending ? "Analyzing…" : "Analyze with AI"}
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={
                    createWorkSubmission.isPending ||
                    !workDone.trim() ||
                    !formattedWork ||
                    pointsToAdd == null ||
                    !effortLevel
                  }
                >
                  Save entry
                </Button>
              </div>
              {!formattedWork && workDone.trim() ? (
                <p style={{ margin: 0, fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                  Analyze with AI first — points depend on how hard the work was, not just that you
                  logged something.
                </p>
              ) : null}
            </form>
          </section>
          )
        ) : null}
      </div>
    </>
  );
}
