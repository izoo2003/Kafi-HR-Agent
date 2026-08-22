import { useAuth } from "../../hooks/useAuth";
import { SIDEBAR_SUB_ICON } from "../../constants/hrModuleIcons";
import { SidebarSubnavLink } from "../../components/layout/SidebarSubnavLink";

type Props = {
  open: boolean;
};

export function UserManagementSectionMenus({ open }: Props) {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("users", "write");

  if (!open) return null;

  return (
    <div className="sidebar__subnav">
      <SidebarSubnavLink to="/admin/users" end icon={SIDEBAR_SUB_ICON.viewUsers}>
        View Users
      </SidebarSubnavLink>
      {canWrite ? (
        <SidebarSubnavLink to="/admin/users/new" icon={SIDEBAR_SUB_ICON.createUsers}>
          Create Users
        </SidebarSubnavLink>
      ) : null}
    </div>
  );
}
