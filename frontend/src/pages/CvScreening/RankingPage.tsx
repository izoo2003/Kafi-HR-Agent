import { Link, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { usePatchCandidate, useRanking } from "../../hooks/useJobDescriptions";
import { downloadReport, rerank } from "../../api/jobDescriptions";
import { CANDIDATE_STATUS_LABELS } from "../../constants/statusLabels";
import { useQueryClient } from "@tanstack/react-query";

export function RankingPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const ranking = useRanking(jobId);
  const patch = usePatchCandidate();
  const qc = useQueryClient();

  return (
    <>
      <PageHeader
        title="Ranking"
        breadcrumb="CV Screening / Ranking"
        actions={
          <>
            <Button
              variant="secondary"
              onClick={async () => {
                await rerank(jobId);
                qc.invalidateQueries({ queryKey: ["ranking", jobId] });
              }}
            >
              Recompute Ranking
            </Button>
            <Button
              variant="primary"
              onClick={async () => {
                const blob = await downloadReport(jobId);
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `ranking_job_${jobId}.xlsx`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              Export Excel Report
            </Button>
          </>
        }
      />
      <div className="page">
        {ranking.isLoading ? <Spinner /> : null}
        {ranking.data && ranking.data.length === 0 ? (
          <EmptyState
            title="No rankings yet"
            description="Upload and score candidates first, then recompute ranking."
          />
        ) : null}
        {ranking.data && ranking.data.length > 0 ? (
          <Table headers={["Rank", "Name", "Email", "Score", "Status", "Actions"]}>
            {ranking.data.map((r) => (
              <tr key={r.candidateId} data-status={r.status}>
                <td className="num">{r.rankPosition}</td>
                <td>
                  <Link to={`/candidates/${r.candidateId}`}>{r.fullName ?? "—"}</Link>
                  {r.pendingManualReview ? " (pending review)" : ""}
                </td>
                <td>{r.email ?? "—"}</td>
                <td className="num">{r.totalScore.toFixed(1)}</td>
                <td>
                  <StatusBadge status={r.status}>
                    {CANDIDATE_STATUS_LABELS[r.status as keyof typeof CANDIDATE_STATUS_LABELS] ?? r.status}
                  </StatusBadge>
                </td>
                <td style={{ display: "flex", gap: 8 }}>
                  <Button
                    variant="positive"
                    onClick={() => patch.mutate({ id: r.candidateId, status: "shortlisted" })}
                  >
                    Shortlist Candidate
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => patch.mutate({ id: r.candidateId, status: "rejected" })}
                  >
                    Reject Candidate
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        ) : null}
      </div>
    </>
  );
}
