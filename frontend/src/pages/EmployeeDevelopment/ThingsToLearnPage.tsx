import { useEffect, useState, type CSSProperties } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import { useEmployees } from "../../hooks/useEmployees";
import {
  useEmployeeTrainingList,
  useUpdateEmployeeTrainingStatus,
} from "../../hooks/useEmployeeTraining";
import { isSelfService } from "../../lib/selfService";
import type { TrainingStatus } from "../../types/employeeTraining";

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

function statusRail(status: TrainingStatus): string {
  if (status === "completed") return "positive";
  if (status === "in_progress") return "warning";
  return "info";
}

function statusBadge(status: TrainingStatus): string {
  if (status === "completed") return "approved";
  if (status === "in_progress") return "pending";
  return "draft";
}

export function ThingsToLearnPage() {
  const { user } = useAuth();
  const selfService = isSelfService(user);
  const [filterEmployeeId, setFilterEmployeeId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const employees = useEmployees({
    status: "active",
    page: 1,
    pageSize: 200,
    enabled: !selfService,
  });

  const listEmployeeId = selfService
    ? user?.linkedEmployeeId ?? null
    : filterEmployeeId === ""
      ? null
      : Number(filterEmployeeId);

  const list = useEmployeeTrainingList(listEmployeeId, true);
  const updateStatus = useUpdateEmployeeTrainingStatus();

  useEffect(() => {
    setError(null);
  }, [listEmployeeId]);

  async function setStatus(assignmentId: number, status: TrainingStatus) {
    setError(null);
    try {
      await updateStatus.mutateAsync({ assignmentId, status });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update status");
    }
  }

  return (
    <>
      <PageHeader title="Things To Learn" breadcrumb="Employee Development / Things To Learn" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <Card>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Courses assigned to you for development. Mark them in progress or completed as you work
            through them.
          </p>
          {!selfService ? (
            <label className="form-field" style={{ maxWidth: 420 }}>
              <span className="form-field__label">Filter by employee</span>
              <select
                className="form-field__input"
                style={selectStyle}
                value={filterEmployeeId === "" ? "" : String(filterEmployeeId)}
                onChange={(e) =>
                  setFilterEmployeeId(e.target.value ? Number(e.target.value) : "")
                }
              >
                <option value="">All employees</option>
                {(employees.data?.items ?? []).map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.fullName} ({e.employeeCode})
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          {error ? (
            <p style={{ color: "var(--color-status-critical)", marginBottom: 0 }}>{error}</p>
          ) : null}
        </Card>

        {list.isLoading ? <Spinner label="Loading Things To Learn" /> : null}
        {list.isError ? (
          <EmptyState
            title="Could not load courses"
            description={
              list.error instanceof ApiError ? list.error.message : "Please try again."
            }
          />
        ) : null}

        {!list.isLoading && (list.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title="Nothing to learn yet"
            description={
              selfService
                ? "When HR assigns training courses for you, they will appear here."
                : "No training assignments match this filter. Assign courses from Employee Training."
            }
          />
        ) : null}

        <div
          style={{
            display: "grid",
            gap: "var(--space-3)",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))",
          }}
        >
          {(list.data?.items ?? []).map((row) => (
            <Card key={row.id} status={statusRail(row.status)}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "var(--space-2)",
                  alignItems: "flex-start",
                }}
              >
                <h2 style={{ margin: 0, fontSize: "var(--text-base)" }}>{row.title}</h2>
                <StatusBadge status={statusBadge(row.status)}>
                  {row.status.replace("_", " ")}
                </StatusBadge>
              </div>
              <div style={{ marginTop: "var(--space-2)" }}>
                <StatusBadge status={row.level === "advanced" ? "info" : "pending"}>
                  {row.level}
                </StatusBadge>
                {row.provider ? (
                  <span
                    style={{
                      marginLeft: "var(--space-2)",
                      fontSize: "var(--text-xs)",
                      color: "var(--color-text-muted)",
                    }}
                  >
                    {row.provider}
                  </span>
                ) : null}
              </div>
              {!selfService && row.employeeName ? (
                <p
                  style={{
                    margin: "var(--space-2) 0 0",
                    fontSize: "var(--text-sm)",
                    color: "var(--color-text-muted)",
                  }}
                >
                  {row.employeeName}
                  {row.employeeCode ? ` · ${row.employeeCode}` : ""}
                  {row.roleTitle ? ` · ${row.roleTitle}` : ""}
                </p>
              ) : null}
              <p
                style={{
                  margin: "var(--space-3) 0 0",
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-secondary)",
                  lineHeight: 1.5,
                }}
              >
                {row.description}
              </p>
              <p
                style={{
                  margin: "var(--space-2) 0 0",
                  fontSize: "var(--text-xs)",
                  color: "var(--color-text-muted)",
                }}
              >
                Topic: {row.topicPrompt}
                {row.departmentName ? ` · ${row.departmentName}` : ""}
              </p>
              {row.urlHint ? (
                <p
                  className="font-data"
                  style={{
                    margin: "var(--space-2) 0 0",
                    fontSize: "var(--text-xs)",
                    color: "var(--color-accent)",
                    wordBreak: "break-word",
                  }}
                >
                  {row.urlHint.startsWith("http") ? (
                    <a href={row.urlHint} target="_blank" rel="noreferrer">
                      {row.urlHint}
                    </a>
                  ) : (
                    row.urlHint
                  )}
                </p>
              ) : null}
              <div
                style={{
                  display: "flex",
                  gap: "var(--space-2)",
                  flexWrap: "wrap",
                  marginTop: "var(--space-4)",
                }}
              >
                {row.status !== "in_progress" && row.status !== "completed" ? (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={updateStatus.isPending}
                    onClick={() => void setStatus(row.id, "in_progress")}
                  >
                    Mark in progress
                  </Button>
                ) : null}
                {row.status !== "completed" ? (
                  <Button
                    type="button"
                    disabled={updateStatus.isPending}
                    onClick={() => void setStatus(row.id, "completed")}
                  >
                    Mark completed
                  </Button>
                ) : null}
                {row.status === "completed" ? (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={updateStatus.isPending}
                    onClick={() => void setStatus(row.id, "assigned")}
                  >
                    Reopen
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </>
  );
}
