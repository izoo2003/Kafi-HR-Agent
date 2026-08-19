import { NavLink } from "react-router-dom";

export function EmployeeSectionMenus({ open }: { open: boolean }) {
  if (!open) return null;

  return (
    <div className="sidebar__subnav">
      <NavLink
        to="/employees/departments"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Departments
      </NavLink>
      <NavLink
        to="/employees/letters/appointment"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Appointment letter
      </NavLink>
      <NavLink
        to="/employees/letters/contract"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Contract letter
      </NavLink>
    </div>
  );
}
