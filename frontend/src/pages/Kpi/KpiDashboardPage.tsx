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
import { useDepartments, useEmployees } from "../../hooks/useEmployees";
import { isSelfService } from "../../lib/selfService";
import {
  useAiSuggestKpiEntry,
  useCreateKpiWorkSubmission,
  useDepartmentKpiSummary,
  useEmployeeKpiSummary,
  useGlobalKpiSummary,
  useMarkKpiPeriodReviewed,
} from "../../hooks/useKpi";

function monthRange(ym: string): { from: string; to: string } {
  const [y, m] = ym.split("-").map(Number);
  const from = `${y}-${String(m).padStart(2, "0")}-01`;
  const last = new Date(y, m, 0).getDate();
  const to = `${y}-${String(m).padStart(2, "0")}-${String(last).padStart(2, "0")}`;
  return { from, to };
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
  const [departmentId, setDepartmentId] = useState<number | "">(
    selfService && user?.departmentId ? user.departmentId : "",
  );
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(
    selfService ? (user?.linkedEmployeeId ?? null) : null,
  );
  const range = useMemo(() => monthRange(month), [month]);
  const deptSelected = selfService ? !!user?.departmentId : departmentId !== "";

  const departmentName = useMemo(() => {
    if (!user?.departmentId) return "—";
    return (
      (departments.data ?? []).find((d) => d.id === user.departmentId)?.name ??
      `Department #${user.departmentId}`
    );
  }, [departments.data, user?.departmentId]);

  const employees = useEmployees({
    page: 1,
    pageSize: 200,
    status: "active",
    departmentId: deptSelected ? (selfService ? user?.departmentId : departmentId) : undefined,
    enabled: deptSelected && !selfService,
  });
  const summary = useDepartmentKpiSummary(
    selfService ? null : deptSelected ? departmentId : null,
    range.from,
    range.to,
  );
  const globalSummary = useGlobalKpiSummary(range.from, range.to);
  const empSummary = useEmployeeKpiSummary(
    selfService ? (user?.linkedEmployeeId ?? null) : selectedEmployeeId,
    range.from,
    range.to,
  );
  const createWorkSubmission = useCreateKpiWorkSubmission();
  const markReviewed = useMarkKpiPeriodReviewed();
  const aiSuggest = useAiSuggestKpiEntry();

  const [workDone, setWorkDone] = useState("");
  const [formattedWork, setFormattedWork] = useState<string | null>(null);
  const [pointsToAdd, setPointsToAdd] = useState<number | null>(null);
  const [aiReasoning, setAiReasoning] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const empName = useMemo(() => {
    const map = new Map((employees.data?.items ?? []).map((e) => [e.id, e.fullName]));
    return (id: number) => map.get(id) ?? `Employee #${id}`;
  }, [employees.data]);

  async function onSaveWorkSubmission(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const text = (formattedWork ?? workDone).trim();
    if (!text) {
      setError("Describe the work done before saving.");
      return;
    }
    try {
      await createWorkSubmission.mutateAsync({
        periodStart: range.from,
        periodEnd: range.to,
        workText: workDone.trim(),
        formattedWork: formattedWork ?? undefined,
        pointsToAdd: pointsToAdd ?? undefined,
      });
      setWorkDone("");
      setFormattedWork(null);
      setPointsToAdd(null);
      setAiReasoning(null);
      setMessage("Work saved — department and global KPI scores updated.");
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
        departmentId: Number(departmentId || user?.departmentId),
        employeeId: Number(selfService ? user?.linkedEmployeeId : selectedEmployeeId),
        periodStart: range.from,
        periodEnd: range.to,
        text: workDone.trim(),
      });
      setFormattedWork(res.formattedWork ?? workDone.trim());
      setPointsToAdd(res.pointsToAdd ?? 1);
      setMessage("AI formatted your work — review below, then save.");
      setAiReasoning(res.reasoning);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI suggest failed");
    }
  }

  async function onMarkReviewed() {
    if (departmentId === "") return;
    setError(null);
    setMessage(null);
    try {
      const res = await markReviewed.mutateAsync({
        departmentId,
        periodStart: range.from,
        periodEnd: range.to,
      });
      setMessage(res.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to mark period reviewed");
    }
  }

  const empItems = employees.data?.items ?? [];

  return (
    <>
      <PageHeader
        title={selfService ? "My KPI dashboard" : "KPI Dashboard"}
        breadcrumb="KPI / Dashboard"
        actions={null}
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
          <label className="form-field">
            <span className="form-field__label">Period (month)</span>
            <input
              className="form-field__input"
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
            />
          </label>
          {selfService ? (
            <label className="form-field">
              <span className="form-field__label">Department</span>
              <input
                className="form-field__input"
                value={departmentName}
                readOnly
                disabled
              />
            </label>
          ) : (
            <label className="form-field">
              <span className="form-field__label">Department</span>
              <select
                className="form-field__input"
                value={departmentId}
                onChange={(e) => {
                  setDepartmentId(e.target.value ? Number(e.target.value) : "");
                }}
              >
                <option value="">Select…</option>
                {(departments.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        {!deptSelected && !selfService ? (
          <EmptyState
            title="Select a department"
            description="Department rollups, employee scores, and period close live here."
          />
        ) : (
          <>
            {selfService ? (
              empSummary.isLoading ? (
                <Spinner label="Loading your KPIs" />
              ) : empSummary.data ? (
                <>
                  <Card status={empSummary.data.departmentBand}>
                    <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Department score</h2>
                    <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                      {empSummary.data.departmentScore.toFixed(1)}
                      <span style={{ fontSize: "var(--text-base)", color: "var(--color-text-muted)" }}>
                        {" "}
                        / 10
                      </span>
                    </div>
                    <StatusBadge status={empSummary.data.departmentBand}>
                      {KPI_STATUS_LABELS[empSummary.data.departmentBand]}
                    </StatusBadge>
                  </Card>
                  <div
                    style={{
                      display: "grid",
                      gap: "var(--space-3)",
                      gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                    }}
                  >
                    <Card status={empSummary.data.globalBand}>
                      <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                        {empSummary.data.globalScore.toFixed(1)} / 10
                      </div>
                      <div>Global score</div>
                      <StatusBadge status={empSummary.data.globalBand}>
                        {KPI_STATUS_LABELS[empSummary.data.globalBand]}
                      </StatusBadge>
                    </Card>
                    <Card>
                      <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                        {empSummary.data.submissionCount}
                      </div>
                      <div>Your submissions this period</div>
                    </Card>
                  </div>
                  {empSummary.data.workItems.length > 0 ? (
                    <section className="card">
                      <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Work logged</h2>
                      <ul style={{ margin: 0, paddingLeft: "var(--space-5)" }}>
                        {empSummary.data.workItems.map((entry, idx) => (
                          <li key={idx} style={{ marginBottom: "var(--space-3)" }}>
                            {entry.text}
                          </li>
                        ))}
                      </ul>
                    </section>
                  ) : (
                    <EmptyState
                      title="No work logged yet"
                      description="Describe what you accomplished this period below, analyze with AI, then save."
                    />
                  )}
                </>
              ) : (
                <EmptyState
                  title="Ready to log work"
                  description="Describe what you did this period below."
                />
              )
            ) : (
              <>
                {summary.isLoading || globalSummary.isLoading ? <Spinner label="Loading KPI summary" /> : null}
                {summary.isError || globalSummary.isError ? (
                  <p style={{ color: "var(--color-status-critical)" }}>
                    Could not load department summary.
                  </p>
                ) : null}

                {summary.data && globalSummary.data ? (
                  <>
                    <div
                      style={{
                        display: "grid",
                        gap: "var(--space-3)",
                        gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                      }}
                    >
                      <Card status={globalSummary.data.band}>
                        <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                          {globalSummary.data.overallScore.toFixed(1)} / 10
                        </div>
                        <div>Global overall</div>
                        <StatusBadge status={globalSummary.data.band}>
                          {KPI_STATUS_LABELS[globalSummary.data.band]}
                        </StatusBadge>
                      </Card>
                      <Card status={summary.data.band}>
                        <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                          {summary.data.overallScore.toFixed(1)}
                          <span
                            style={{
                              fontSize: "var(--text-base)",
                              color: "var(--color-text-muted)",
                            }}
                          >
                            {" "}
                            / 10
                          </span>
                        </div>
                        <div>Dept overall</div>
                        <StatusBadge status={summary.data.band}>
                          {KPI_STATUS_LABELS[summary.data.band]}
                        </StatusBadge>
                      </Card>
                      <Card>
                        <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                          {Math.round(summary.data.completeness * 100)}%
                        </div>
                        <div>
                          Submitted ({summary.data.entriesRecorded}/{summary.data.entriesExpected})
                        </div>
                      </Card>
                    </div>

                    <section>
                      <h2 style={{ fontSize: "var(--text-lg)" }}>Department ranking</h2>
                      <Table headers={["Department", "Score", "Band", "Submitted"]}>
                        {globalSummary.data.departments.map((dept) => (
                          <tr key={dept.departmentId} data-status={dept.band}>
                            <td>{dept.departmentName}</td>
                            <td className="font-data">{dept.overallScore.toFixed(1)} / 10</td>
                            <td>
                              <StatusBadge status={dept.band}>
                                {KPI_STATUS_LABELS[dept.band]}
                              </StatusBadge>
                            </td>
                            <td className="font-data">
                              {dept.entriesRecorded}/{dept.entriesExpected}
                            </td>
                          </tr>
                        ))}
                      </Table>
                    </section>

                    {canApprove ? (
                      <div>
                        <Button
                          variant="primary"
                          onClick={onMarkReviewed}
                          disabled={markReviewed.isPending}
                        >
                          Mark period reviewed
                        </Button>
                      </div>
                    ) : null}

                    <section>
                      <h2 style={{ fontSize: "var(--text-lg)" }}>Employee contributions</h2>
                      <Table headers={["Employee", "Contribution", "Band", "Entries"]}>
                        {summary.data.employees.map((emp) => (
                          <tr
                            key={emp.employeeId}
                            data-status={emp.band}
                            style={{ cursor: "pointer" }}
                            onClick={() => setSelectedEmployeeId(emp.employeeId)}
                          >
                            <td>{empName(emp.employeeId)}</td>
                            <td className="font-data">
                              {emp.contributionScore.toFixed(1)} / 10
                            </td>
                            <td>
                              <StatusBadge status={emp.band}>
                                {KPI_STATUS_LABELS[emp.band]}
                              </StatusBadge>
                            </td>
                            <td className="font-data">
                              {emp.submissionCount}
                            </td>
                          </tr>
                        ))}
                      </Table>
                    </section>

                    {selectedEmployeeId != null && empSummary.data ? (
                      <Card status={empSummary.data.departmentBand}>
                        <h3 style={{ marginTop: 0 }}>
                          {empName(selectedEmployeeId)} — work submitted
                        </h3>
                        {empSummary.data.workItems.length === 0 ? (
                          <p>No work submitted for this period.</p>
                        ) : (
                          <ul>
                            {empSummary.data.workItems.map((entry, idx) => (
                              <li key={idx} style={{ marginBottom: "var(--space-2)" }}>
                                {entry.text}
                              </li>
                            ))}
                          </ul>
                        )}
                        <p style={{ marginBottom: 0 }}>
                          Contribution:{" "}
                          <span className="font-data">
                            {empSummary.data.contributionScore.toFixed(1)} / 10
                          </span>
                        </p>
                      </Card>
                    ) : null}
                  </>
                ) : null}
              </>
            )}

            {canWrite && selfService ? (
              <section className="card">
                <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Log work done</h2>
                <form
                  onSubmit={onSaveWorkSubmission}
                  style={{ display: "grid", gap: "var(--space-3)" }}
                >
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
                      }}
                      placeholder="Describe what you accomplished this period…"
                      required
                    />
                  </label>
                  {formattedWork ? (
                    <div
                      className="card"
                      style={{
                        background: "var(--color-accent-subtle)",
                        padding: "var(--space-3)",
                      }}
                    >
                      <strong>AI preview</strong>
                      <p style={{ margin: "var(--space-2) 0" }}>{formattedWork}</p>
                      {pointsToAdd != null ? (
                        <p
                          style={{
                            margin: 0,
                            color: "var(--color-text-secondary)",
                            fontSize: "var(--text-sm)",
                          }}
                        >
                          Adds <span className="font-data">{pointsToAdd.toFixed(1)}</span> to your
                          contribution score
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                  {aiReasoning ? (
                    <p style={{ margin: 0, color: "var(--color-text-secondary)" }}>
                      AI: {aiReasoning}
                    </p>
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
                      disabled={createWorkSubmission.isPending || !workDone.trim()}
                    >
                      Save entry
                    </Button>
                  </div>
                </form>
              </section>
            ) : null}
          </>
        )}
      </div>
    </>
  );
}
