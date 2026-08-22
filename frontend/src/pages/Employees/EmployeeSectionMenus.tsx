import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { HrModuleIcon } from "../../components/ui/HrModuleIcon";
import { SIDEBAR_SUB_ICON } from "../../constants/hrModuleIcons";
import {
  SidebarSubnavItem,
  SidebarSubnavLink,
} from "../../components/layout/SidebarSubnavLink";

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
      {canWrite ? (
        <>
          <button
            type="button"
            className={`sidebar__sublink${docVerificationOpen ? " sidebar__sublink--open" : ""}`}
            aria-expanded={docVerificationOpen}
            onClick={() => setDocVerificationOpen((value) => !value)}
          >
            <HrModuleIcon icon={SIDEBAR_SUB_ICON.documentVerification} size="sm" />
            <span className="sidebar__sublink-label">Employees Document Verification</span>
            <ChevronDown size={16} className="sidebar__subchevron" aria-hidden />
          </button>
          {docVerificationOpen ? (
            <ul className="sidebar__sublist">
              <li>
                <SidebarSubnavItem to="/employees/verify-cnic" icon={SIDEBAR_SUB_ICON.verifyCnic}>
                  Verify my CNIC
                </SidebarSubnavItem>
              </li>
              <li>
                <SidebarSubnavItem
                  to="/employees/verify-education"
                  icon={SIDEBAR_SUB_ICON.verifyEducation}
                  title="AI-assisted check only — not an official board or HEC verification"
                >
                  Verify education documents
                </SidebarSubnavItem>
              </li>
            </ul>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
