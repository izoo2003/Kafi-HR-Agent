import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import { useLocalDraftPersist } from "../../hooks/useLocalDraftPersist";
import { useDepartments } from "../../hooks/useEmployees";
import {
  useEmployeeDevelopmentEmployees,
  useEmployeeDevelopmentSelection,
} from "../../hooks/useEmployeeDevelopmentEmployees";
import {
  useAssignEmployeeTraining,
  useEmployeeTrainingList,
  useRecommendEmployeeTraining,
} from "../../hooks/useEmployeeTraining";
import { clearLocalDraft, formatDraftRestoredMessage, loadLocalDraft } from "../../lib/localDraft";
import type { TrainingCourseRecommendation } from "../../types/employeeTraining";

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

function courseKey(c: TrainingCourseRecommendation): string {
  return `${c.title}|${c.level}|${c.provider ?? ""}`;
}

function statusBadge(status: string): string {
  if (status === "completed") return "approved";
  if (status === "in_progress") return "pending";
  return "draft";
}

export function EmployeeTrainingPage() {
  const { hasPermission } = useAuth();
  const { selfService, canListEmployees, employees } = useEmployeeDevelopmentEmployees();
  const canWrite = hasPermission("kpi", "write") && !selfService && canListEmployees;
  const { employeeId, setEmployeeId: setEmployeeIdBase } = useEmployeeDevelopmentSelection(
    Boolean(employees.data?.items.length),
    employees.data?.items,
  );
  const [topic, setTopic] = useState("");
  const [promptOpen, setPromptOpen] = useState(false);
  const [recommendations, setRecommendations] = useState<TrainingCourseRecommendation[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [lastTopic, setLastTopic] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [draftMessage, setDraftMessage] = useState<string | null>(null);
  const restoredRef = useRef(false);

  const departments = useDepartments();
  const assigned = useEmployeeTrainingList(
    employeeId === "" ? null : Number(employeeId),
    employeeId !== "",
  );
  const recommend = useRecommendEmployeeTraining();
  const assign = useAssignEmployeeTraining();

  const selectedEmployee = useMemo(
    () => (employees.data?.items ?? []).find((e) => e.id === employeeId),
    [employees.data, employeeId],
  );
  const departmentName = useMemo(() => {
    if (!selectedEmployee) return null;
    return (
      (departments.data ?? []).find((d) => d.id === selectedEmployee.departmentId)?.name ?? null
    );
  }, [departments.data, selectedEmployee]);

  const draftScope = "employee_training";
  useLocalDraftPersist({
    scope: draftScope,
    dirty:
      employeeId !== "" ||
      topic.trim().length > 0 ||
      promptOpen ||
      recommendations.length > 0 ||
      selected.size > 0 ||
      lastTopic.trim().length > 0,
    enabled: canWrite,
    data: {
      employeeId,
      topic,
      promptOpen,
      recommendations,
      selected: [...selected],
      lastTopic,
    },
    isEmpty: (d) =>
      d.employeeId === "" &&
      !d.topic.trim() &&
      !d.promptOpen &&
      d.recommendations.length === 0 &&
      d.selected.length === 0 &&
      !d.lastTopic.trim(),
  });

  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    const draft = loadLocalDraft<{
      employeeId: number | "";
      topic: string;
      promptOpen: boolean;
      recommendations: TrainingCourseRecommendation[];
      selected: string[];
      lastTopic: string;
    }>(draftScope);
    if (!draft?.data) return;
    setEmployeeIdBase(draft.data.employeeId ?? "");
    setTopic(draft.data.topic ?? "");
    setPromptOpen(Boolean(draft.data.promptOpen));
    setRecommendations(draft.data.recommendations ?? []);
    setSelected(new Set(draft.data.selected ?? []));
    setLastTopic(draft.data.lastTopic ?? "");
    setDraftMessage(formatDraftRestoredMessage(draft.savedAt, "training draft"));
  }, [setEmployeeIdBase]);

  function onEmployeeChange(id: number | "") {
    setEmployeeIdBase(id);
    setRecommendations([]);
    setSelected(new Set());
    setTopic("");
    setLastTopic("");
    setError(null);
    setSuccess(null);
    if (id !== "") setPromptOpen(true);
  }

  async function onRecommend() {
    if (employeeId === "" || !topic.trim()) return;
    setError(null);
    setSuccess(null);
    try {
      const res = await recommend.mutateAsync({
        employeeId: Number(employeeId),
        topic: topic.trim(),
      });
      setRecommendations(res.courses);
      setLastTopic(res.topic);
      setSelected(new Set(res.courses.map(courseKey)));
      setPromptOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not recommend courses");
    }
  }

  async function onAssign() {
    if (employeeId === "" || !lastTopic || selected.size === 0) return;
    const courses = recommendations.filter((c) => selected.has(courseKey(c)));
    if (!courses.length) return;
    setError(null);
    try {
      const res = await assign.mutateAsync({
        employeeId: Number(employeeId),
        topic: lastTopic,
        courses,
      });
      clearLocalDraft(draftScope);
      setSuccess(`Assigned ${res.items.length} course(s). They appear under Things To Learn.`);
      setRecommendations([]);
      setSelected(new Set());
      setTopic("");
      setLastTopic("");
      setPromptOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not assign courses");
    }
  }

  function toggleCourse(c: TrainingCourseRecommendation) {
    const key = courseKey(c);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  if (!canWrite) {
    return (
      <>
        <PageHeader title="Employee Training" breadcrumb="Employee Development / Employee Training" />
        <div className="page">
          <EmptyState
            title={selfService ? "HR assigns training for you" : "Write access required"}
            description={
              selfService
                ? "Assigned courses appear under Things To Learn on your account."
                : canListEmployees
                  ? "You can view assigned courses under Things To Learn. Assigning training requires KPI write permission."
                  : "You need employees read access to pick someone for training. View your own courses under Things To Learn."
            }
          />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Employee Training" breadcrumb="Employee Development / Employee Training" />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <Card>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Select an employee, describe the training focus, and assign intermediate/advanced courses
            tailored to their department and role. Assigned courses show up for them under Things To
            Learn.
          </p>
          <label className="form-field" style={{ maxWidth: 420 }}>
            <span className="form-field__label">Employee</span>
            <select
              className="form-field__input"
              style={selectStyle}
              value={employeeId === "" ? "" : String(employeeId)}
              onChange={(e) =>
                onEmployeeChange(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Select employee…</option>
              {employees.isLoading ? (
                <option value="" disabled>
                  Loading employees…
                </option>
              ) : employees.isError ? (
                <option value="" disabled>
                  Could not load employees
                </option>
              ) : (
                (employees.data?.items ?? []).map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.fullName} ({e.employeeCode}) — {e.roleTitle}
                  </option>
                ))
              )}
            </select>
            {employees.isError ? (
              <span className="form-field__error">
                {employees.error instanceof ApiError
                  ? employees.error.message
                  : "Could not load the employee list."}
              </span>
            ) : null}
          </label>
          {selectedEmployee ? (
            <p style={{ marginBottom: 0, fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
              Role: {selectedEmployee.roleTitle}
              {departmentName ? ` · ${departmentName}` : ""}
            </p>
          ) : null}
          {error ? (
            <p style={{ color: "var(--color-status-critical)", marginBottom: 0 }}>{error}</p>
          ) : null}
          {draftMessage ? (
            <p style={{ color: "var(--color-status-warning)", marginBottom: 0 }}>{draftMessage}</p>
          ) : null}
          {success ? (
            <p style={{ color: "var(--color-status-positive)", marginBottom: 0 }}>{success}</p>
          ) : null}
        </Card>

        {promptOpen && employeeId !== "" ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Training topic</h2>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              What kind of training or course do you want them to learn?
            </p>
            <label className="form-field">
              <span className="form-field__label">Topic</span>
              <textarea
                className="form-field__input"
                rows={3}
                placeholder="e.g. advanced Excel for commodity trading reports, leadership for supervisors…"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              />
            </label>
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              <Button
                type="button"
                disabled={recommend.isPending || topic.trim().length < 3}
                onClick={() => void onRecommend()}
              >
                {recommend.isPending ? "Recommending…" : "Recommend courses"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setPromptOpen(false)}>
                Cancel
              </Button>
            </div>
          </Card>
        ) : null}

        {!promptOpen && employeeId !== "" ? (
          <div>
            <Button type="button" variant="secondary" onClick={() => setPromptOpen(true)}>
              Ask for a new training topic
            </Button>
          </div>
        ) : null}

        {recommend.isPending ? <Spinner label="Generating course recommendations" /> : null}

        {recommendations.length > 0 ? (
          <section style={{ display: "grid", gap: "var(--space-3)" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "var(--space-3)",
                flexWrap: "wrap",
              }}
            >
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                Recommended for “{lastTopic}”
              </h2>
              <Button
                type="button"
                disabled={assign.isPending || selected.size === 0}
                onClick={() => void onAssign()}
              >
                {assign.isPending ? "Assigning…" : `Assign selected (${selected.size})`}
              </Button>
            </div>
            <div
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 280px), 1fr))",
              }}
            >
              {recommendations.map((c) => {
                const key = courseKey(c);
                const isOn = selected.has(key);
                return (
                  <Card
                    key={key}
                    status={c.level === "advanced" ? "info" : "warning"}
                  >
                    <label
                      style={{
                        display: "flex",
                        gap: "var(--space-2)",
                        alignItems: "flex-start",
                        cursor: "pointer",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isOn}
                        onChange={() => toggleCourse(c)}
                        style={{ marginTop: 4 }}
                      />
                      <div>
                        <div style={{ fontWeight: "var(--weight-semibold)" }}>{c.title}</div>
                        <div style={{ marginTop: "var(--space-1)" }}>
                          <StatusBadge status={c.level === "advanced" ? "info" : "pending"}>
                            {c.level}
                          </StatusBadge>
                          {c.provider ? (
                            <span
                              style={{
                                marginLeft: "var(--space-2)",
                                fontSize: "var(--text-xs)",
                                color: "var(--color-text-muted)",
                              }}
                            >
                              {c.provider}
                            </span>
                          ) : null}
                        </div>
                        <p
                          style={{
                            margin: "var(--space-2) 0 0",
                            fontSize: "var(--text-sm)",
                            color: "var(--color-text-secondary)",
                          }}
                        >
                          {c.description}
                        </p>
                        {c.urlHint ? (
                          <p
                            className="font-data"
                            style={{
                              margin: "var(--space-2) 0 0",
                              fontSize: "var(--text-xs)",
                              color: "var(--color-text-muted)",
                              wordBreak: "break-word",
                            }}
                          >
                            {c.urlHint}
                          </p>
                        ) : null}
                      </div>
                    </label>
                  </Card>
                );
              })}
            </div>
          </section>
        ) : null}

        {employeeId !== "" ? (
          <section>
            <h2 style={{ margin: "0 0 var(--space-3)", fontSize: "var(--text-lg)" }}>
              Already assigned
            </h2>
            {assigned.isLoading ? <Spinner label="Loading assignments" /> : null}
            {!assigned.isLoading && (assigned.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                title="No courses assigned yet"
                description="Recommend and assign courses above. The employee will see them under Things To Learn."
              />
            ) : null}
            {(assigned.data?.items.length ?? 0) > 0 ? (
              <Table headers={["Course", "Level", "Provider", "Topic", "Status", "Assigned"]}>
                {(assigned.data?.items ?? []).map((row) => (
                  <tr
                    key={row.id}
                    data-status={
                      row.status === "completed"
                        ? "positive"
                        : row.status === "in_progress"
                          ? "warning"
                          : "neutral"
                    }
                  >
                    <td>
                      <div style={{ fontWeight: "var(--weight-medium)" }}>{row.title}</div>
                      <div
                        style={{
                          fontSize: "var(--text-xs)",
                          color: "var(--color-text-muted)",
                          maxWidth: 320,
                        }}
                      >
                        {row.description}
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={row.level === "advanced" ? "info" : "pending"}>
                        {row.level}
                      </StatusBadge>
                    </td>
                    <td>{row.provider || "—"}</td>
                    <td style={{ maxWidth: 200 }}>{row.topicPrompt}</td>
                    <td>
                      <StatusBadge status={statusBadge(row.status)}>
                        {row.status.replace("_", " ")}
                      </StatusBadge>
                    </td>
                    <td className="font-data" style={{ fontSize: "var(--text-xs)" }}>
                      {row.assignedAt.slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </Table>
            ) : null}
          </section>
        ) : null}
      </div>
    </>
  );
}
