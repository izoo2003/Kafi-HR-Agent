import { PageHeader } from "../../components/layout/AppShell";
import { EmptyState } from "../../components/ui/EmptyState";

export function KpiDefinitionsPage() {
  return (
    <>
      <PageHeader title="KPI Definitions" breadcrumb="KPI / Definitions" actions={null} />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        <EmptyState
          title="Definitions are automatic"
          description="Employees submit work from the KPI dashboard. Those submissions build department scores, and department scores build the global KPI rating."
        />
      </div>
    </>
  );
}
