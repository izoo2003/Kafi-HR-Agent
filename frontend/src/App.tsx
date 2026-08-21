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
import { EmployeeFormPage } from "./pages/Employees/EmployeeFormPage";
import { VerifyCnicPage } from "./pages/Employees/VerifyCnicPage";
import { DepartmentManagePage } from "./pages/Employees/DepartmentManagePage";
import { EmployeeLettersPage } from "./pages/Employees/EmployeeLettersPage";
import { AttendanceOverviewPage } from "./pages/Attendance/AttendanceOverviewPage";
import { AttendanceRecordsPage } from "./pages/Attendance/AttendanceRecordsPage";
import { AttendancePeriodReportPage } from "./pages/Attendance/AttendancePeriodReportPage";
import { LeaveRequestsPage } from "./pages/Attendance/LeaveRequestsPage";
import { PayrollRunListPage } from "./pages/Payroll/PayrollRunListPage";
import { PayrollRunDetailPage } from "./pages/Payroll/PayrollRunDetailPage";
import { PayslipDetailPage } from "./pages/Payroll/PayslipDetailPage";
import { SalaryAdvancesPage } from "./pages/Payroll/SalaryAdvancesPage";
import { TaxSlabsPage } from "./pages/Payroll/TaxSlabsPage";
import { SalaryComputePage } from "./pages/Payroll/SalaryComputePage";
import { KpiDefinitionsPage } from "./pages/Kpi/KpiDefinitionsPage";
import { KpiDashboardPage } from "./pages/Kpi/KpiDashboardPage";
import { EmployeePerformancePage } from "./pages/EmployeeDevelopment/EmployeePerformancePage";
import { EmployeeTrainingPage } from "./pages/EmployeeDevelopment/EmployeeTrainingPage";
import { ThingsToLearnPage } from "./pages/EmployeeDevelopment/ThingsToLearnPage";
import {
  AuditLogPage,
  DashboardPage,
  SystemConfigPage,
} from "./pages/AdminPanel/DashboardPage";
import { CreateUserPage, UserManagementPage } from "./pages/AdminPanel/UserManagementPage";
import { HrPoliciesPage } from "./pages/HrPolicies/HrPoliciesPage";
import { NotAuthorizedPage, NotFoundPage } from "./pages/SystemPages";
import { useAuth } from "./hooks/useAuth";
import { homePath } from "./lib/selfService";

function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={homePath(user)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<Navigate to="/login" replace />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/onboarding" element={<HrPoliciesPage />} />
          <Route path="/hr-policies" element={<Navigate to="/onboarding" replace />} />

          <Route element={<RequirePermission module="employees" />}>
            <Route path="/employees" element={<EmployeeListPage />} />
            <Route path="/employees/new" element={<EmployeeFormPage />} />
            <Route path="/employees/verify-cnic" element={<VerifyCnicPage />} />
            <Route path="/employees/departments" element={<DepartmentManagePage />} />
            <Route
              path="/employees/letters/appointment"
              element={<EmployeeLettersPage kind="appointment" />}
            />
            <Route
              path="/employees/letters/contract"
              element={<EmployeeLettersPage kind="contract" />}
            />
            <Route path="/employees/:id" element={<EmployeeFormPage />} />
            <Route path="/departments" element={<DepartmentManagePage />} />
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
          <Route element={<RequirePermission module="attendance" level="write" />}>
            <Route path="/attendance/period-report" element={<AttendancePeriodReportPage />} />
          </Route>

          <Route element={<RequirePermission module="payroll" />}>
            <Route path="/payroll/runs" element={<PayrollRunListPage />} />
            <Route path="/payroll/compute" element={<SalaryComputePage />} />
            <Route path="/payroll/tax-slabs" element={<TaxSlabsPage />} />
            <Route path="/payroll/runs/:id" element={<PayrollRunDetailPage />} />
            <Route path="/payroll/payslips/:id" element={<PayslipDetailPage />} />
            <Route path="/payroll/advances" element={<SalaryAdvancesPage />} />
          </Route>

          <Route element={<RequirePermission module="kpi" />}>
            <Route path="/kpi/definitions" element={<KpiDefinitionsPage />} />
            <Route path="/kpi/dashboard" element={<KpiDashboardPage />} />
            <Route
              path="/employee-development/performance"
              element={<EmployeePerformancePage />}
            />
            <Route
              path="/employee-development/training"
              element={<EmployeeTrainingPage />}
            />
            <Route
              path="/employee-development/things-to-learn"
              element={<ThingsToLearnPage />}
            />
            <Route
              path="/employee-development"
              element={<Navigate to="/employee-development/performance" replace />}
            />
          </Route>

          <Route element={<RequirePermission module="admin_panel" />}>
            <Route path="/admin/dashboard" element={<DashboardPage />} />
            <Route path="/admin/audit-log" element={<AuditLogPage />} />
            <Route path="/admin/config" element={<SystemConfigPage />} />
          </Route>

          <Route element={<RequirePermission module="users" />}>
            <Route path="/admin/users" element={<UserManagementPage />} />
            <Route path="/admin/users/new" element={<CreateUserPage />} />
          </Route>

          <Route path="/not-authorized" element={<NotAuthorizedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
