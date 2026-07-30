import { PageHeader } from "../../components/layout/AppShell";
import { EmptyState } from "../../components/ui/EmptyState";

export function PayrollRunListPage() {
  return (
    <>
      <PageHeader title="Payroll Runs" breadcrumb="Payroll / Runs" />
      <div className="page">
        <EmptyState
          title="No payroll runs yet"
          description="Create a draft run for a period, generate payslips from attendance, then submit for approval. Full flow arrives with FEATURE_PAYROLL.md."
        />
      </div>
    </>
  );
}

export function PayrollRunDetailPage() {
  return (
    <>
      <PageHeader title="Payroll Run" breadcrumb="Payroll / Runs / Detail" />
      <div className="page">
        <EmptyState title="Run detail" description="Payslip list and approval actions pending." />
      </div>
    </>
  );
}

export function PayslipDetailPage() {
  return (
    <>
      <PageHeader title="Payslip" breadcrumb="Payroll / Payslip" />
      <div className="page">
        <EmptyState title="Payslip" description="Line items and PDF download pending." />
      </div>
    </>
  );
}

export function SalaryAdvancesPage() {
  return (
    <>
      <PageHeader title="Salary Advances" breadcrumb="Payroll / Advances" />
      <div className="page">
        <EmptyState title="Advances" description="Advance request and recovery tracking pending." />
      </div>
    </>
  );
}
