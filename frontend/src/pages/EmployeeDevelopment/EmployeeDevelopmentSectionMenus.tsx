import { NavLink } from "react-router-dom";

export function EmployeeDevelopmentSectionMenus({ open }: { open: boolean }) {
  if (!open) return null;

  return (
    <div className="sidebar__subnav">
      <NavLink
        to="/employee-development/performance"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Employee Performance
      </NavLink>
      <NavLink
        to="/employee-development/training"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Employee Training
      </NavLink>
      <NavLink
        to="/employee-development/things-to-learn"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Things To Learn
      </NavLink>
    </div>
  );
}
