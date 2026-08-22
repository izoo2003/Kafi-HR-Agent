import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { useJobDescriptions, useSyncCvSources, useUnassignedCandidates } from "../../hooks/useJobDescriptions";
import { useDepartments } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { ApiError } from "../../api/client";

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
  const unassigned = useUnassignedCandidates({ page: 1, pageSize: 1 });
  const sync = useSyncCvSources();
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
    const [duplicates, setDuplicates] = useState<
      Array<{
        source: string;
        sourceRef: string;
        existingCandidateId: number;
        existingJobDescriptionId: number | null;
        existingStatus: string;
        existingFullName: string | null;
        existingEmail: string | null;
        submittedFullName: string | null;
        submittedEmail: string | null;
      }>
    >([]);

  const deptName = useMemo(() => {
    const map = new Map((departments.data ?? []).map((d) => [d.id, d.name]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [departments.data]);

  const openCount = jobs.data?.total ?? 0;
  const hasAnyJobs = (allJobs.data?.total ?? 0) > 0;
  const unassignedCount = unassigned.data?.total ?? 0;

  async function handleSync() {
    setSyncError(null);
    setSyncMessage(null);
      setDuplicates([]);
    try {
      const result = await sync.mutateAsync();
      const sourceLabel: Record<string, string> = {
        webmail: "Webmail",
        outlook: "Outlook",
        whatsapp: "WhatsApp",
        gmail: "Gmail",
        google_form: "Google Form",
      };
      let msg = `Fetched ${result.totalFetched} new — ${result.autoMatched} matched, ${result.unassigned} unassigned`;
      if (result.duplicatesSkipped > 0) msg += ` (${result.duplicatesSkipped} already in system, skipped)`;
      if ((result.restoredFiles ?? 0) > 0) {
        msg += `, restored ${result.restoredFiles} missing CV file(s)`;
      }
      const notConfigured = result.sources.filter((s) => !s.configured);
      if (notConfigured.length > 0) {
        msg += `. Not connected: ${notConfigured.map((s) => sourceLabel[s.source] ?? s.source).join(", ")}.`;
      }
      // Surface why (e.g. missing IMAP_PASSWORD on Railway) — not only the label list.
      const details = result.sources
        .filter((s) => s.message)
        .map((s) => `${sourceLabel[s.source] ?? s.source}: ${s.message}`)
        .join(" | ");
      if (details) msg += ` — ${details}`;
      setSyncMessage(msg);
      setDuplicates(result.duplicates ?? []);
    } catch (err) {
      if (err instanceof ApiError) {
        setSyncError(err.message);
      } else if (err instanceof TypeError) {
        setSyncError(
          "Sync timed out or lost connection. Click Sync CVs again — Google Form and webmail import in smaller batches now.",
        );
      } else {
        setSyncError(err instanceof Error ? err.message : "Sync failed");
      }
    }
  }

  return (
    <>
      <PageHeader
        title="CV Screening"
        breadcrumb="CV Screening"
        actions={
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button variant="primary" disabled={sync.isPending} onClick={handleSync}>
              {sync.isPending ? "Syncing…" : "Sync CVs"}
            </Button>
            <Link to="/job-descriptions">
              <Button variant="secondary">Manage job postings</Button>
            </Link>
          </div>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--color-text-muted)" }}>
          Select an open role to upload CVs, review candidates, and open the ranking. Click{" "}
          <strong>Sync CVs</strong> to pull new submissions from hr@kafi-group.com webmail and the
          Google Form — sync is manual (not instant). Google Form responses can take 30–60 seconds
          to appear in the linked sheet after someone submits.
        </p>

        {syncError ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{syncError}</p> : null}
        {syncMessage ? <p style={{ color: "var(--color-status-info)", margin: 0 }}>{syncMessage}</p> : null}
        {duplicates.length > 0 ? (
          <div style={{ marginTop: "var(--space-3)" }}>
            <p style={{ margin: 0, fontWeight: "var(--weight-semibold)" }}>Possible duplicates</p>
            <p style={{ margin: "var(--space-1) 0 0", color: "var(--color-text-secondary)" }}>
              These submissions were skipped because a candidate with the same <code>source_ref</code> already
              exists. If the email was applied to a different job, you can re-route the existing candidate from
              its detail page.
            </p>
            <Table headers={["Submitted", "Existing", "Job", "Status"]}>
              {duplicates.map((d) => (
                <tr key={`${d.source}-${d.sourceRef}-${d.existingCandidateId}`} data-status="warning">
                  <td>
                    {d.submittedFullName ?? d.submittedEmail ?? d.sourceRef}
                    <div style={{ color: "var(--color-text-muted)", fontSize: "var(--text-xs)" }}>{d.source}</div>
                  </td>
                  <td>
                    <Link to={`/candidates/${d.existingCandidateId}`}>
                      {d.existingFullName ?? `Candidate #${d.existingCandidateId}`}
                    </Link>
                    <div style={{ color: "var(--color-text-muted)", fontSize: "var(--text-xs)" }}>{d.sourceRef}</div>
                  </td>
                  <td>
                    {d.existingJobDescriptionId ? `JD #${d.existingJobDescriptionId}` : "Unassigned"}
                  </td>
                  <td>{d.existingStatus}</td>
                </tr>
              ))}
            </Table>
          </div>
        ) : null}

        {unassignedCount > 0 ? (
          <Link
            to="/cv-screening/unassigned"
            style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)", width: "fit-content" }}
          >
            <StatusBadge status="warning">{unassignedCount} unassigned CV{unassignedCount === 1 ? "" : "s"}</StatusBadge>
            <span>Needs manual routing to a job →</span>
          </Link>
        ) : null}

        {jobs.isLoading ? <Spinner label="Loading open roles" /> : null}

        {!jobs.isLoading && openCount === 0 ? (
          <EmptyState
            title="No open roles to screen"
            description={
              hasAnyJobs
                ? "Open a job description (set status to Open), then return here to upload CVs."
                : "Create a job description with skills first, set it to Open, then screen CVs here."
            }
            actionLabel="Go to Job Postings"
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
                      <Link to={`/job-descriptions/${j.id}`}>View posting</Link>
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
