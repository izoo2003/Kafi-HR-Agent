import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";

export function EmployeeSectionMenus({ open }: { open: boolean }) {
  const location = useLocation();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("employees", "write");
  const onVerifyCnic = location.pathname.startsWith("/employees/verify-cnic");
  const onVerifyEducation = location.pathname.startsWith("/employees/verify-education");
  const onDocVerification = onVerifyCnic || onVerifyEducation;
  const [docVerificationOpen, setDocVerificationOpen] = useState(onDocVerification);

  useEffect(() => {
    if (onDocVerification) setDocVerificationOpen(true);
  }, [onDocVerification]);

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
      {canWrite ? (
        <>
          <button
            type="button"
            className={`sidebar__sublink${docVerificationOpen ? " sidebar__sublink--open" : ""}`}
            aria-expanded={docVerificationOpen}
            onClick={() => setDocVerificationOpen((value) => !value)}
          >
            <span>Employees Document Verification</span>
            <ChevronDown size={14} className="sidebar__subchevron" aria-hidden />
          </button>
          {docVerificationOpen ? (
            <ul className="sidebar__sublist">
              <li>
                <NavLink
                  to="/employees/verify-cnic"
                  className={({ isActive }) =>
                    `sidebar__subitem${isActive ? " sidebar__subitem--active" : ""}`
                  }
                >
                  Verify my CNIC
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/employees/verify-education"
                  className={({ isActive }) =>
                    `sidebar__subitem${isActive ? " sidebar__subitem--active" : ""}`
                  }
                  title="AI-assisted check only — not an official board or HEC verification"
                >
                  Verify education documents
                </NavLink>
              </li>
            </ul>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
