import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useJobDescriptions } from "../../hooks/useJobDescriptions";
import { useDepartments } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { useMemo } from "react";

const JD_STATUS: Record<string, string> = {
  draft: "Draft",
  open: "Open",
  closed: "Closed",
};

/** CV Screening hub — pick a role, then upload CVs / view ranking. */
export function CvScreeningHubPage() {
  const { page, pageSize, setPage, params } = usePagination();
  const jobs = useJobDescriptions({ ...params, status: "open" });
  const allJobs = useJobDescriptions({ page: 1, pageSize: 100 });
  const departments = useDepartments();

  const deptName = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  const openCount = jobs.data?.total ?? 0;
  const hasAnyJobs = (allJobs.data?.total ?? 0) > 0;

  return (
    <>
      <PageHeader
        title="CV Screening"
        breadcrumb="CV Screening"
        actions={
          <Link to="/job-descriptions">
            <Button variant="secondary">Manage job descriptions</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-muted)" }}>
          Select an open role to upload CVs, review candidates, and open the ranking.
        </p>

        {jobs.isLoading ? <Spinner label="Loading open roles" /> : null}

        {!jobs.isLoading && openCount === 0 ? (
          <EmptyState
            title="No open roles to screen"
            description={
              hasAnyJobs
                ? "Open a job description (set status to Open), then return here to upload CVs."
                : "Create a job description with skills first, set it to Open, then screen CVs here."
            }
            actionLabel="Go to Job Descriptions"
            onAction={() => {
              window.location.href = "/job-descriptions";
            }}
          />
        ) : null}

        {jobs.data && jobs.data.items.length > 0 ? (
          <>
            <Table headers={["Role", "Department", "Status", "Screening"]}>
              {jobs.data.items.map((j) => (
                <tr key={j.id} data-status="positive">
                  <td>{j.title}</td>
                  <td>{deptName(j.departmentId)}</td>
                  <td>
                    <StatusBadge status="approved">
                      {JD_STATUS[j.status] ?? j.status}
                    </StatusBadge>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                      <Link to={`/job-descriptions/${j.id}/candidates`}>
                        <Button type="button" variant="primary">
                          Candidates & upload
                        </Button>
                      </Link>
                      <Link to={`/job-descriptions/${j.id}/ranking`}>
                        <Button type="button" variant="secondary">
                          Ranking
                        </Button>
                      </Link>
                      <Link to={`/job-descriptions/${j.id}`}>View JD</Link>
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={jobs.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
    </>
  );
}
