import { SidebarSubnavLink } from "../../components/layout/SidebarSubnavLink";
import { SIDEBAR_SUB_ICON } from "../../constants/hrModuleIcons";

export function EmployeeSectionMenus({ open }: { open: boolean }) {
  if (!open) return null;

  return (
    <div className="sidebar__subnav">
      <SidebarSubnavLink to="/employees/departments" icon={SIDEBAR_SUB_ICON.departments}>
        Departments
      </SidebarSubnavLink>
      <SidebarSubnavLink
        to="/employees/letters/appointment"
        icon={SIDEBAR_SUB_ICON.appointmentLetter}
      >
        Appointment letter
      </SidebarSubnavLink>
      <SidebarSubnavLink to="/employees/letters/contract" icon={SIDEBAR_SUB_ICON.contractLetter}>
        Contract letter
      </SidebarSubnavLink>
    </div>
  );
}
