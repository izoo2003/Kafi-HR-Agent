import { SidebarSubnavLink } from "../../components/layout/SidebarSubnavLink";
import { SIDEBAR_SUB_ICON } from "../../constants/hrModuleIcons";

export function DocumentVerificationSectionMenus({ open }: { open: boolean }) {
  if (!open) return null;

  return (
    <div className="sidebar__subnav">
      <SidebarSubnavLink to="/employees/verify-cnic" icon={SIDEBAR_SUB_ICON.verifyCnic}>
        Verify my CNIC
      </SidebarSubnavLink>
      <SidebarSubnavLink
        to="/employees/verify-education"
        icon={SIDEBAR_SUB_ICON.verifyEducation}
        title="AI-assisted check only — not an official board or HEC verification"
      >
        Verify education documents
      </SidebarSubnavLink>
    </div>
  );
}
