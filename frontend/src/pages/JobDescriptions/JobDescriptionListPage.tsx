import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useJobDescriptions, useDeleteJobDescription } from "../../hooks/useJobDescriptions";
import { useDepartments, useEmployees, useUpdateEmployee } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { useAuth } from "../../hooks/useAuth";
import { ApiError } from "../../api/client";
import type { Employee } from "../../types/employees";

const JD_STATUS: Record<string, string> = {
  draft: "Draft",
  open: "Open",
  closed: "Closed",
};

type ViewMode = "postings" | "descriptions";

function EmployeeJobDescriptionRow({
  employee,
  departmentName,
  canEdit,
}: {
  employee: Employee;
  departmentName: string;
  canEdit: boolean;
}) {
  const update = useUpdateEmployee();
  const [text, setText] = useState(employee.jobDescriptionText ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dirty = text !== (employee.jobDescriptionText ?? "");

  useEffect(() => {
    setText(employee.jobDescriptionText ?? "");
  }, [employee.jobDescriptionText]);

  async function save() {
    setError(null);
    setMessage(null);
    try {
      await update.mutateAsync({
        id: employee.id,
        payload: { jobDescriptionText: text.trim() || null },
      });
      setMessage("Saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    }
  }

  return (
    <tr key={employee.id} data-status="info">
      <td>
        <div>{employee.fullName}</div>
        <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
          {employee.employeeCode} · {employee.roleTitle}
        </div>
      </td>
      <td>{departmentName}</td>
      <td style={{ minWidth: 320, paddingTop: "var(--space-2)", paddingBottom: "var(--space-2)" }}>
        <textarea
          className="form-field__input"
          rows={3}
          disabled={!canEdit}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Duties, responsibilities, and requirements for this role…"
          style={{ width: "100%", resize: "vertical", fontFamily: "var(--font-ui)" }}
        />
        {error ? (
          <div style={{ color: "var(--color-status-critical)", fontSize: "var(--text-xs)" }}>{error}</div>
        ) : null}
        {message ? (
          <div style={{ color: "var(--color-status-positive)", fontSize: "var(--text-xs)" }}>{message}</div>
        ) : null}
      </td>
      <td>
        {canEdit ? (
          <Button type="button" variant="primary" disabled={!dirty || update.isPending} onClick={save}>
            {update.isPending ? "Saving…" : "Save"}
          </Button>
        ) : (
          "—"
        )}
      </td>
    </tr>
  );
}

function JobDescriptionsView() {
  const { page, pageSize, setPage, params } = usePagination();
  const { hasPermission } = useAuth();
  const canEdit = hasPermission("employees", "write");
  const employees = useEmployees({ ...params, status: "active" });
  const departments = useDepartments();

  const deptName = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  if (employees.isLoading) return <Spinner label="Loading active employees" />;

  if ((employees.data?.total ?? 0) === 0) {
    return (
      <EmptyState
        title="No active employees"
        description="Add employees in the Employees section first. Their internal job descriptions (duties and requirements) will appear here."
        actionLabel="Go to Employees"
        onAction={() => {
          window.location.href = "/employees";
        }}
      />
    );
  }

  return (
    <>
      <p style={{ margin: "0 0 var(--space-4)", color: "var(--color-text-muted)" }}>
        Internal job descriptions for active employees — what they do day to day. These are not hiring
        postings and are not used for CV screening.
      </p>
      <Table headers={["Employee", "Department", "Job description", "Actions"]}>
        {(employees.data?.items ?? []).map((e) => (
          <EmployeeJobDescriptionRow
            key={e.id}
            employee={e}
            departmentName={deptName(e.departmentId)}
            canEdit={canEdit}
          />
        ))}
      </Table>
      <Pagination
        page={page}
        pageSize={pageSize}
        total={employees.data?.total ?? 0}
        onPageChange={setPage}
      />
    </>
  );
}

function JobPostingsView() {
  const { page, pageSize, setPage, params } = usePagination();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("job_descriptions", "write");
  const jobs = useJobDescriptions(params);
  const deleteJob = useDeleteJobDescription();
  const [error, setError] = useState<string | null>(null);

  async function onDelete(id: number, title: string, applicants: number) {
    const applicantNote =
      applicants > 0
        ? ` This will also remove ${applicants} candidate(s) and their CVs.`
        : "";
    if (
      !window.confirm(
        `Delete job posting "${title}"? This cannot be undone.${applicantNote}`,
      )
    ) {
      return;
    }
    setError(null);
    try {
      await deleteJob.mutateAsync(id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete job posting");
    }
  }

  if (jobs.isLoading) return <Spinner label="Loading job postings" />;

  if (jobs.data && jobs.data.items.length === 0) {
    return (
      <EmptyState
        title="No job postings yet"
        description="Create an open role, add skills with level 1 (very low) to 10 (expert), then upload CVs."
        actionLabel="New Job Posting"
        onAction={() => {
          window.location.href = "/job-descriptions/new";
        }}
      />
    );
  }

  return (
    <>
      {error ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{error}</p> : null}
      <Table headers={["Title", "Department", "Status", "Applicants", "Actions"]}>
        {(jobs.data?.items ?? []).map((j) => (
          <tr
            key={j.id}
            data-status={j.status === "open" ? "positive" : j.status === "closed" ? "neutral" : "info"}
          >
            <td>{j.title}</td>
            <td className="num">{j.departmentId}</td>
            <td>
              <StatusBadge
                status={j.status === "open" ? "approved" : j.status === "closed" ? "draft" : "scored"}
              >
                {JD_STATUS[j.status] ?? j.status}
              </StatusBadge>
            </td>
            <td className="num">{j.applicantsCount ?? 0}</td>
            <td>
              <Link to={`/job-descriptions/${j.id}`}>View</Link>
              {" · "}
              <Link to={`/job-descriptions/${j.id}/candidates`}>Candidates</Link>
              {" · "}
              <Link to={`/job-descriptions/${j.id}/ranking`}>Ranking</Link>
              {canWrite ? (
                <>
                  {" · "}
                  <button
                    type="button"
                    onClick={() => void onDelete(j.id, j.title, j.applicantsCount ?? 0)}
                    disabled={deleteJob.isPending}
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      color: "var(--color-status-critical)",
                      cursor: deleteJob.isPending ? "not-allowed" : "pointer",
                      font: "inherit",
                      textDecoration: "underline",
                    }}
                  >
                    Delete
                  </button>
                </>
              ) : null}
            </td>
          </tr>
        ))}
      </Table>
      <Pagination
        page={page}
        pageSize={pageSize}
        total={jobs.data?.total ?? 0}
        onPageChange={setPage}
      />
    </>
  );
}

export function JobDescriptionListPage() {
  const [view, setView] = useState<ViewMode>("postings");

  return (
    <>
      <PageHeader
        title="Job Postings"
        breadcrumb="Job Postings"
        actions={
          view === "postings" ? (
            <Link to="/job-descriptions/new">
              <Button variant="primary">New Job Posting</Button>
            </Link>
          ) : null
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-4)" }}>
        <label className="form-field" style={{ maxWidth: 280 }}>
          <span className="form-field__label">View</span>
          <select
            className="form-field__input"
            value={view}
            onChange={(e) => setView(e.target.value as ViewMode)}
          >
            <option value="postings">Job Postings</option>
            <option value="descriptions">Job Descriptions</option>
          </select>
        </label>

        {view === "postings" ? <JobPostingsView /> : <JobDescriptionsView />}
      </div>
    </>
  );
}
