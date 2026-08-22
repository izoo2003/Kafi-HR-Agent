import { SIDEBAR_SUB_ICON } from "../../constants/hrModuleIcons";
import { SidebarSubnavLink } from "../../components/layout/SidebarSubnavLink";

type Props = {
  open: boolean;
  /** HR/staff with employees read — show assign/manage subsections. */
  canManage?: boolean;
};

export function EmployeeDevelopmentSectionMenus({ open, canManage = true }: Props) {
  if (!open) return null;

  return (
    <div className="sidebar__subnav">
      <SidebarSubnavLink
        to="/employee-development/performance"
        icon={SIDEBAR_SUB_ICON.employeePerformance}
      >
        Employee Performance
      </SidebarSubnavLink>
      {canManage ? (
        <>
          <SidebarSubnavLink
            to="/employee-development/training"
            icon={SIDEBAR_SUB_ICON.employeeTraining}
          >
            Employee Training
          </SidebarSubnavLink>
          <SidebarSubnavLink
            to="/employee-development/resignation"
            icon={SIDEBAR_SUB_ICON.employeeResignation}
          >
            Employee Resignation
          </SidebarSubnavLink>
        </>
      ) : null}
      <SidebarSubnavLink to="/employee-development/things-to-learn" icon={SIDEBAR_SUB_ICON.thingsToLearn}>
        Things To Learn
      </SidebarSubnavLink>
    </div>
  );
}
