import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { RequireAuth, RequirePermission } from "./components/layout/RequirePermission";
import { LoginPage } from "./pages/Auth/LoginPage";
import { JobDescriptionListPage } from "./pages/JobDescriptions/JobDescriptionListPage";
import { JobDescriptionDetailPage } from "./pages/JobDescriptions/JobDescriptionDetailPage";
import { JobDescriptionFormPage } from "./pages/JobDescriptions/JobDescriptionFormPage";
import { CandidateListPage } from "./pages/CvScreening/CandidateListPage";
import { CandidateDetailPage } from "./pages/CvScreening/CandidateDetailPage";
import { RankingPage } from "./pages/CvScreening/RankingPage";
import { CvScreeningHubPage } from "./pages/CvScreening/CvScreeningHubPage";
import { UnassignedCandidatesPage } from "./pages/CvScreening/UnassignedCandidatesPage";
import { EmployeeListPage } from "./pages/Employees/EmployeeListPage";
import { AttendanceOverviewPage } from "./pages/Attendance/AttendanceOverviewPage";
import { AttendanceRecordsPage } from "./pages/Attendance/AttendanceRecordsPage";
import { LeaveRequestsPage } from "./pages/Attendance/LeaveRequestsPage";
import { PayrollRunListPage } from "./pages/Payroll/PayrollRunListPage";
import { PayrollRunDetailPage } from "./pages/Payroll/PayrollRunDetailPage";
import { PayslipDetailPage } from "./pages/Payroll/PayslipDetailPage";
import { SalaryAdvancesPage } from "./pages/Payroll/SalaryAdvancesPage";
import { KpiDefinitionsPage } from "./pages/Kpi/KpiDefinitionsPage";
import { KpiDashboardPage } from "./pages/Kpi/KpiDashboardPage";
import {
  AuditLogPage,
  DashboardPage,
  SystemConfigPage,
  UserManagementPage,
} from "./pages/AdminPanel/DashboardPage";
import { NotAuthorizedPage, NotFoundPage } from "./pages/SystemPages";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />

          <Route element={<RequirePermission module="employees" />}>
            <Route path="/employees" element={<EmployeeListPage />} />
            <Route path="/departments" element={<EmployeeListPage />} />
          </Route>

          <Route element={<RequirePermission module="job_descriptions" />}>
            <Route path="/job-descriptions" element={<JobDescriptionListPage />} />
            <Route path="/job-descriptions/new" element={<JobDescriptionFormPage />} />
            <Route path="/job-descriptions/:id/edit" element={<JobDescriptionFormPage />} />
            <Route path="/job-descriptions/:id" element={<JobDescriptionDetailPage />} />
          </Route>

          <Route element={<RequirePermission module="cv_screening" />}>
            <Route path="/cv-screening" element={<CvScreeningHubPage />} />
            <Route path="/cv-screening/unassigned" element={<UnassignedCandidatesPage />} />
            <Route path="/job-descriptions/:id/candidates" element={<CandidateListPage />} />
            <Route path="/job-descriptions/:id/ranking" element={<RankingPage />} />
            <Route path="/candidates" element={<Navigate to="/cv-screening" replace />} />
            <Route path="/candidates/:id" element={<CandidateDetailPage />} />
          </Route>

          <Route element={<RequirePermission module="attendance" />}>
            <Route path="/attendance" element={<AttendanceOverviewPage />} />
            <Route path="/attendance/records" element={<AttendanceRecordsPage />} />
            <Route path="/attendance/leave-requests" element={<LeaveRequestsPage />} />
          </Route>

          <Route element={<RequirePermission module="payroll" />}>
            <Route path="/payroll/runs" element={<PayrollRunListPage />} />
            <Route path="/payroll/runs/:id" element={<PayrollRunDetailPage />} />
            <Route path="/payroll/payslips/:id" element={<PayslipDetailPage />} />
            <Route path="/payroll/advances" element={<SalaryAdvancesPage />} />
          </Route>

          <Route element={<RequirePermission module="kpi" />}>
            <Route path="/kpi/definitions" element={<KpiDefinitionsPage />} />
            <Route path="/kpi/dashboard" element={<KpiDashboardPage />} />
          </Route>

          <Route element={<RequirePermission module="admin_panel" />}>
            <Route path="/admin/dashboard" element={<DashboardPage />} />
            <Route path="/admin/audit-log" element={<AuditLogPage />} />
            <Route path="/admin/config" element={<SystemConfigPage />} />
          </Route>

          <Route element={<RequirePermission module="users" />}>
            <Route path="/admin/users" element={<UserManagementPage />} />
          </Route>

          <Route path="/not-authorized" element={<NotAuthorizedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
