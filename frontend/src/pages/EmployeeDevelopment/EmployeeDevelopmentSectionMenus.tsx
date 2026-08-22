import { NavLink } from "react-router-dom";

type Props = {
  open: boolean;
  /** HR/staff with employees read — show assign/manage subsections. */
  canManage?: boolean;
};

export function EmployeeDevelopmentSectionMenus({ open, canManage = true }: Props) {
  if (!open) return null;

  return (
    <div className="sidebar__subnav">
      <NavLink
        to="/employee-development/performance"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Employee Performance
      </NavLink>
      {canManage ? (
        <>
          <NavLink
            to="/employee-development/training"
            className={({ isActive }) =>
              `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`
            }
          >
            Employee Training
          </NavLink>
          <NavLink
            to="/employee-development/resignation"
            className={({ isActive }) =>
              `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`
            }
          >
            Employee Resignation
          </NavLink>
        </>
      ) : null}
      <NavLink
        to="/employee-development/things-to-learn"
        className={({ isActive }) => `sidebar__sublink${isActive ? " sidebar__sublink--active" : ""}`}
      >
        Things To Learn
      </NavLink>
    </div>
  );
}
