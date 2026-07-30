import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import { useDepartments } from "../../hooks/useEmployees";
import {
  useArchiveKpiDefinition,
  useCreateKpiDefinition,
  useKpiDefinitions,
} from "../../hooks/useKpi";
import type { KpiReviewPeriod } from "../../types/kpi";

export function KpiDefinitionsPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("kpi", "write");
  const departments = useDepartments();
  const [departmentId, setDepartmentId] = useState<number | "">("");
  const definitions = useKpiDefinitions(
    departmentId === "" ? undefined : { departmentId },
  );
  const createDef = useCreateKpiDefinition();
  const archiveDef = useArchiveKpiDefinition();

  const [form, setForm] = useState({
    name: "",
    description: "",
    measurementUnit: "%",
    targetValue: "",
    weight: "",
    reviewPeriod: "monthly" as KpiReviewPeriod,
  });
  const [error, setError] = useState<string | null>(null);

  const weightSum = useMemo(
    () => (definitions.data ?? []).reduce((s, d) => s + Number(d.weight ?? 0), 0),
    [definitions.data],
  );

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (departmentId === "") {
      setError("Select a department");
      return;
    }
    try {
      await createDef.mutateAsync({
        departmentId,
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        measurementUnit: form.measurementUnit.trim() || undefined,
        targetValue: Number(form.targetValue),
        weight: Number(form.weight),
        reviewPeriod: form.reviewPeriod,
      });
      setForm({
        name: "",
        description: "",
        measurementUnit: form.measurementUnit,
        targetValue: "",
        weight: "",
        reviewPeriod: form.reviewPeriod,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create KPI");
    }
  }

  return (
    <>
      <PageHeader
        title="KPI Definitions"
        breadcrumb="KPI / Definitions"
        actions={
          <Link to="/kpi/dashboard">
            <Button variant="secondary">Dashboard</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}

        <label className="form-field" style={{ maxWidth: 280 }}>
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

        {departmentId !== "" ? (
          <p className="font-data" style={{ margin: 0 }}>
            Active weight sum: {weightSum.toFixed(3)}
            {Math.abs(weightSum - 1) > 0.001 && (definitions.data?.length ?? 0) > 0
              ? " — must equal 1.0 before recording is complete"
              : weightSum > 0
                ? " ✓"
                : ""}
          </p>
        ) : null}

        {definitions.isLoading ? <Spinner label="Loading definitions" /> : null}

        {!definitions.isLoading && (definitions.data?.length ?? 0) === 0 ? (
          <EmptyState
            title="No KPI definitions"
            description="Create per-department targets and weights. Active weights must sum to 1.0."
          />
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Department</th>
                <th>Target</th>
                <th>Unit</th>
                <th>Weight</th>
                <th>Period</th>
                {canWrite ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {(definitions.data ?? []).map((d) => {
                const deptName =
                  (departments.data ?? []).find((x) => x.id === d.departmentId)?.name ??
                  String(d.departmentId);
                return (
                  <tr key={d.id}>
                    <td>{d.name}</td>
                    <td>{deptName}</td>
                    <td className="font-data">{d.targetValue}</td>
                    <td>{d.measurementUnit ?? "—"}</td>
                    <td className="font-data">{d.weight}</td>
                    <td>{d.reviewPeriod}</td>
                    {canWrite ? (
                      <td>
                        <Button
                          variant="secondary"
                          onClick={async () => {
                            setError(null);
                            try {
                              await archiveDef.mutateAsync(d.id);
                            } catch (err) {
                              setError(
                                err instanceof ApiError ? err.message : "Archive failed",
                              );
                            }
                          }}
                        >
                          Archive
                        </Button>
                      </td>
                    ) : null}
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}

        {canWrite ? (
          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Add KPI definition</h2>
            <form
              onSubmit={onCreate}
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              }}
            >
              <label className="form-field">
                <span className="form-field__label">Department</span>
                <select
                  className="form-field__input"
                  required
                  value={departmentId === "" ? "" : departmentId}
                  onChange={(e) =>
                    setDepartmentId(e.target.value ? Number(e.target.value) : "")
                  }
                >
                  <option value="">Select…</option>
                  {(departments.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <FormField
                label="Name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
              <FormField
                label="Target"
                type="number"
                step="any"
                value={form.targetValue}
                onChange={(e) => setForm({ ...form, targetValue: e.target.value })}
                required
              />
              <FormField
                label="Weight (0–1)"
                type="number"
                step="0.01"
                min="0.01"
                max="1"
                value={form.weight}
                onChange={(e) => setForm({ ...form, weight: e.target.value })}
                required
              />
              <FormField
                label="Unit"
                value={form.measurementUnit}
                onChange={(e) => setForm({ ...form, measurementUnit: e.target.value })}
              />
              <label className="form-field">
                <span className="form-field__label">Review period</span>
                <select
                  className="form-field__input"
                  value={form.reviewPeriod}
                  onChange={(e) =>
                    setForm({ ...form, reviewPeriod: e.target.value as KpiReviewPeriod })
                  }
                >
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="annual">Annual</option>
                </select>
              </label>
              <FormField
                label="Description"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
              <div style={{ alignSelf: "end" }}>
                <Button type="submit" variant="primary" disabled={createDef.isPending}>
                  Create
                </Button>
              </div>
            </form>
          </section>
        ) : null}
      </div>
    </>
  );
}
