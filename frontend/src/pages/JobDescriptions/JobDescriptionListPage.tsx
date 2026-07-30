import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useJobDescriptions } from "../../hooks/useJobDescriptions";
import { usePagination } from "../../hooks/usePagination";
import { CANDIDATE_STATUS_LABELS } from "../../constants/statusLabels";

const JD_STATUS: Record<string, string> = {
  draft: "Draft",
  open: "Open",
  closed: "Closed",
};

export function JobDescriptionListPage() {
  const { page, pageSize, setPage, params } = usePagination();
  const jobs = useJobDescriptions(params);

  return (
    <>
      <PageHeader
        title="Job Descriptions"
        breadcrumb="Job Descriptions"
        actions={
          <Link to="/job-descriptions/new">
            <Button variant="primary">New Job Description</Button>
          </Link>
        }
      />
      <div className="page">
        {jobs.isLoading ? <Spinner label="Loading jobs" /> : null}
        {jobs.data && jobs.data.items.length === 0 ? (
          <EmptyState
            title="No job descriptions yet"
            description="Create an open role, add skills with level 1 (very low) to 10 (expert), then upload CVs."
            actionLabel="New Job Description"
            onAction={() => { window.location.href = "/job-descriptions/new"; }}
          />
        ) : null}
        {jobs.data && jobs.data.items.length > 0 ? (
          <>
            <Table headers={["Title", "Department", "Status", "Actions"]}>
              {jobs.data.items.map((j) => (
                <tr key={j.id} data-status={j.status === "open" ? "positive" : j.status === "closed" ? "neutral" : "info"}>
                  <td>{j.title}</td>
                  <td className="num">{j.departmentId}</td>
                  <td>
                    <StatusBadge status={j.status === "open" ? "approved" : j.status === "closed" ? "draft" : "scored"}>
                      {JD_STATUS[j.status] ?? j.status}
                    </StatusBadge>
                  </td>
                  <td>
                    <Link to={`/job-descriptions/${j.id}`}>View</Link>
                    {" · "}
                    <Link to={`/job-descriptions/${j.id}/candidates`}>Candidates</Link>
                    {" · "}
                    <Link to={`/job-descriptions/${j.id}/ranking`}>Ranking</Link>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination page={page} pageSize={pageSize} total={jobs.data.total} onPageChange={setPage} />
          </>
        ) : null}
      </div>
    </>
  );
}

void CANDIDATE_STATUS_LABELS;
