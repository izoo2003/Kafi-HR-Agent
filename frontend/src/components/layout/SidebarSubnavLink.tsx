import { NavLink } from "react-router-dom";
import { HrModuleIcon } from "../ui/HrModuleIcon";
import type { HrModuleIconKey } from "../../constants/hrModuleIcons";

type LinkProps = {
  to: string;
  icon: HrModuleIconKey;
  children: React.ReactNode;
  end?: boolean;
  title?: string;
};

export function SidebarSubnavLink({ to, icon, children, end, title }: LinkProps) {
  return (
    <NavLink
      to={to}
      end={end}
      title={title}
      className={({ isActive }) =>
        `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`
      }
    >
      <HrModuleIcon icon={icon} size="sm" />
      <span className="sidebar__sublink-label">{children}</span>
    </NavLink>
  );
}

type ItemProps = {
  to: string;
  icon: HrModuleIconKey;
  children: React.ReactNode;
  title?: string;
};

export function SidebarSubnavItem({ to, icon, children, title }: ItemProps) {
  return (
    <NavLink
      to={to}
      title={title}
      className={({ isActive }) =>
        `sidebar__subitem${isActive ? " sidebar__subitem--active" : ""}`
      }
    >
      <HrModuleIcon icon={icon} size="sm" />
      <span className="sidebar__sublink-label">{children}</span>
    </NavLink>
  );
}
