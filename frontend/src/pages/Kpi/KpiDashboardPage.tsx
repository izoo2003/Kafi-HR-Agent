import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { ApiError } from "../../api/client";
import { KPI_STATUS_LABELS } from "../../constants/statusLabels";
import { useAuth } from "../../hooks/useAuth";
import { useDepartments, useEmployees } from "../../hooks/useEmployees";
import {
  useCreateKpiEntry,
  useDepartmentKpiSummary,
  useEmployeeKpiSummary,
  useKpiDefinitions,
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
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("kpi", "write");
  const canApprove = hasPermission("kpi", "approve");
  const departments = useDepartments();
  const now = new Date();
  const [month, setMonth] = useState(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`,
  );
  const [departmentId, setDepartmentId] = useState<number | "">("");
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const range = useMemo(() => monthRange(month), [month]);

  const employees = useEmployees({
    page: 1,
    pageSize: 100,
    status: "active",
    departmentId: departmentId === "" ? undefined : departmentId,
  });
  const definitions = useKpiDefinitions(
    departmentId === "" ? undefined : { departmentId },
  );
  const summary = useDepartmentKpiSummary(
    departmentId === "" ? null : departmentId,
    range.from,
    range.to,
  );
  const empSummary = useEmployeeKpiSummary(selectedEmployeeId, range.from, range.to);
  const createEntry = useCreateKpiEntry();
  const markReviewed = useMarkKpiPeriodReviewed();

  const [entryForm, setEntryForm] = useState({
    employeeId: "",
    kpiDefinitionId: "",
    actualValue: "",
    notes: "",
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const empName = useMemo(() => {
    const map = new Map((employees.data?.items ?? []).map((e) => [e.id, e.fullName]));
    return (id: number) => map.get(id) ?? `Employee #${id}`;
  }, [employees.data]);

  async function onRecordEntry(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createEntry.mutateAsync({
        employeeId: Number(entryForm.employeeId),
        kpiDefinitionId: Number(entryForm.kpiDefinitionId),
        periodStart: range.from,
        periodEnd: range.to,
        actualValue: Number(entryForm.actualValue),
        notes: entryForm.notes.trim() || undefined,
      });
      setEntryForm({ ...entryForm, actualValue: "", notes: "" });
      setMessage("Entry recorded");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record entry");
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

  return (
    <>
      <PageHeader
        title="KPI Dashboard"
        breadcrumb="KPI / Dashboard"
        actions={
          <Link to="/kpi/definitions">
            <Button variant="secondary">Definitions</Button>
          </Link>
        }
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
          <label className="form-field">
            <span className="form-field__label">Department</span>
            <select
              className="form-field__input"
              value={departmentId}
              onChange={(e) => {
                setDepartmentId(e.target.value ? Number(e.target.value) : "");
                setSelectedEmployeeId(null);
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
        </div>

        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)" }}>{message}</p> : null}

        {departmentId === "" ? (
          <EmptyState
            title="Select a department"
            description="Department rollups, employee scores, and period close live here."
          />
        ) : summary.isLoading ? (
          <Spinner label="Loading KPI summary" />
        ) : summary.data ? (
          <>
            <div
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              }}
            >
              <Card status={summary.data.band}>
                <div className="font-data" style={{ fontSize: "var(--text-2xl)" }}>
                  {summary.data.overallScore.toFixed(1)}
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
                  Completeness ({summary.data.entriesRecorded}/{summary.data.entriesExpected})
                </div>
              </Card>
            </div>

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
              <h2 style={{ fontSize: "var(--text-lg)" }}>KPI breakdown (weakest first)</h2>
              <Table>
                <thead>
                  <tr>
                    <th>KPI</th>
                    <th>Avg score</th>
                    <th>Weight</th>
                    <th>Band</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.kpiBreakdown.map((b) => (
                    <tr key={b.kpiDefinitionId} data-status={b.band}>
                      <td>{b.name}</td>
                      <td className="font-data">{b.averageScore.toFixed(1)}</td>
                      <td className="font-data">{b.weight}</td>
                      <td>
                        <StatusBadge status={b.band}>
                          {KPI_STATUS_LABELS[b.band]}
                        </StatusBadge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </section>

            <section>
              <h2 style={{ fontSize: "var(--text-lg)" }}>Employees</h2>
              <Table>
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Overall</th>
                    <th>Band</th>
                    <th>Entries</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.employees.map((emp) => (
                    <tr
                      key={emp.employeeId}
                      data-status={emp.band}
                      style={{ cursor: "pointer" }}
                      onClick={() => setSelectedEmployeeId(emp.employeeId)}
                    >
                      <td>{empName(emp.employeeId)}</td>
                      <td className="font-data">{emp.overallScore.toFixed(1)}</td>
                      <td>
                        <StatusBadge status={emp.band}>
                          {KPI_STATUS_LABELS[emp.band]}
                        </StatusBadge>
                      </td>
                      <td className="font-data">{emp.entries.length}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </section>

            {selectedEmployeeId != null && empSummary.data ? (
              <Card status={empSummary.data.band}>
                <h3 style={{ marginTop: 0 }}>
                  {empName(selectedEmployeeId)} — detail
                </h3>
                <ul>
                  {empSummary.data.entries.map((en) => (
                    <li key={en.kpiDefinitionId}>
                      {en.name}: actual {en.actual} / target {en.target} →{" "}
                      <span className="font-data">{en.score.toFixed(1)}</span>{" "}
                      <StatusBadge status={en.band}>
                        {KPI_STATUS_LABELS[en.band]}
                      </StatusBadge>
                    </li>
                  ))}
                </ul>
                {(empSummary.data.entries.length ?? 0) === 0 ? (
                  <p>No entries recorded for this period.</p>
                ) : null}
              </Card>
            ) : null}

            {canWrite ? (
              <section className="card">
                <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Record actual</h2>
                <form
                  onSubmit={onRecordEntry}
                  style={{
                    display: "grid",
                    gap: "var(--space-3)",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  }}
                >
                  <label className="form-field">
                    <span className="form-field__label">Employee</span>
                    <select
                      className="form-field__input"
                      required
                      value={entryForm.employeeId}
                      onChange={(e) =>
                        setEntryForm({ ...entryForm, employeeId: e.target.value })
                      }
                    >
                      <option value="">Select…</option>
                      {(employees.data?.items ?? []).map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.fullName}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="form-field">
                    <span className="form-field__label">KPI</span>
                    <select
                      className="form-field__input"
                      required
                      value={entryForm.kpiDefinitionId}
                      onChange={(e) =>
                        setEntryForm({ ...entryForm, kpiDefinitionId: e.target.value })
                      }
                    >
                      <option value="">Select…</option>
                      {(definitions.data ?? []).map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <FormField
                    label="Actual value"
                    type="number"
                    step="any"
                    value={entryForm.actualValue}
                    onChange={(e) =>
                      setEntryForm({ ...entryForm, actualValue: e.target.value })
                    }
                    required
                  />
                  <FormField
                    label="Notes"
                    value={entryForm.notes}
                    onChange={(e) => setEntryForm({ ...entryForm, notes: e.target.value })}
                  />
                  <div style={{ alignSelf: "end" }}>
                    <Button type="submit" variant="primary" disabled={createEntry.isPending}>
                      Save entry
                    </Button>
                  </div>
                </form>
              </section>
            ) : null}
          </>
        ) : (
          <EmptyState title="No summary" description="Could not load department KPI summary." />
        )}
      </div>
    </>
  );
}
