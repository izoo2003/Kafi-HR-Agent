import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import {
  ChevronDown,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { isSelfService } from "../../lib/selfService";
import { Button } from "../ui/Button";
import { HrModuleIcon } from "../ui/HrModuleIcon";
import { SIDEBAR_ICON_BY_PATH } from "../../constants/hrModuleIcons";
import type { HrModuleIconKey } from "../../constants/hrModuleIcons";
import { NotificationBell } from "./NotificationBell";
import { EmployeeSectionMenus } from "../../pages/Employees/EmployeeSectionMenus";
import { EmployeeDevelopmentSectionMenus } from "../../pages/EmployeeDevelopment/EmployeeDevelopmentSectionMenus";
import { UserManagementSectionMenus } from "../../pages/AdminPanel/UserManagementSectionMenus";
import "./AppShell.css";

const NAV: { to: string; label: string; module: string | null; icon: HrModuleIconKey }[] = [
  { to: "/admin/dashboard", label: "Admin", module: "admin_panel", icon: "analyticsDashboard" },
  { to: "/employees", label: "Employees Management", module: "employees", icon: "employeeDirectory" },
  { to: "/job-descriptions", label: "Job Postings", module: "job_descriptions", icon: "recruitment" },
  { to: "/cv-screening", label: "CV Screening", module: "cv_screening", icon: "documentManagement" },
  { to: "/attendance", label: "Attendance", module: "attendance", icon: "attendance" },
  { to: "/payroll/runs", label: "Payroll", module: "payroll", icon: "payroll" },
  { to: "/kpi/dashboard", label: "KPI", module: "kpi", icon: "goalsOkrs" },
  {
    to: "/employee-development/performance",
    label: "Employee Development",
    module: "kpi",
    icon: "trainingDevelopment",
  },
  { to: "/hr-policies", label: "HR Policies", module: null, icon: "compliancePolicies" },
  { to: "/admin/users", label: "User Management", module: "users", icon: "addEmployee" },
];

const SIDEBAR_STORAGE_KEY = "kafi.sidebar.collapsed";

type ShellProps = {
  title: string;
  breadcrumb?: string;
  actions?: ReactNode;
};

export function PageHeader({ title, breadcrumb, actions }: ShellProps) {
  return (
    <header className="topbar">
      <div className="topbar__heading">
        {breadcrumb ? <p className="topbar__crumb">{breadcrumb}</p> : null}
        <h1 className="topbar__title">{title}</h1>
      </div>
      {actions ? <div className="topbar__actions">{actions}</div> : null}
    </header>
  );
}

function readCollapsedPreference(): boolean {
  if (typeof window === "undefined") return false;
  const saved = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
  if (saved === "1") return true;
  if (saved === "0") return false;
  return window.matchMedia("(max-width: 1023px)").matches;
}

export function AppShell() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const selfService = isSelfService(user);
  const isMobile = useMediaQuery("(max-width: 767px)");
  const [collapsed, setCollapsed] = useState(readCollapsedPreference);
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = NAV.filter((item) => {
    if (item.module === null) return true;
    if (selfService && item.module !== "attendance" && item.module !== "kpi") {
      return false;
    }
    return hasPermission(item.module, "read");
  });

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isMobile) setMobileOpen(false);
  }, [isMobile]);

  useEffect(() => {
    if (!isMobile || !mobileOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [isMobile, mobileOpen]);

  function persistCollapsed(next: boolean) {
    setCollapsed(next);
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, next ? "1" : "0");
  }

  function toggleSidebar() {
    if (isMobile) setMobileOpen((open) => !open);
    else persistCollapsed(!collapsed);
  }

  const railCollapsed = !isMobile && collapsed;
  const shellClass = [
    "shell",
    railCollapsed ? "shell--collapsed" : "",
    isMobile && mobileOpen ? "shell--drawer-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={shellClass}>
      {isMobile && mobileOpen ? (
        <button
          type="button"
          className="sidebar__backdrop"
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}
      <aside className="sidebar" id="app-sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__brand-mark">
            <HrModuleIcon icon="hrAiAssistant" size="md" label="Kafi HR" />
          </span>
          <div className="sidebar__brand-text">
            <strong>Kafi HR</strong>
            <span>{selfService ? "My workspace" : "Admin Agent"}</span>
          </div>
          {!isMobile ? (
            <button
              type="button"
              className="sidebar__toggle"
              aria-label={collapsed ? "Open sidebar" : "Close sidebar"}
              aria-expanded={!collapsed}
              aria-controls="app-sidebar"
              onClick={toggleSidebar}
            >
              {collapsed ? <PanelLeftOpen size={20} aria-hidden /> : <PanelLeftClose size={20} aria-hidden />}
            </button>
          ) : (
            <button
              type="button"
              className="sidebar__toggle"
              aria-label="Close menu"
              onClick={() => setMobileOpen(false)}
            >
              <X size={20} aria-hidden />
            </button>
          )}
        </div>
        <nav className="sidebar__nav" aria-label="Modules">
          {navItems.map((item) => {
            const iconKey = SIDEBAR_ICON_BY_PATH[item.to] ?? item.icon;
            const link = (
              <NavLink
                to={item.to}
                title={item.label}
                className={() => {
                  const active =
                    item.to === "/employees"
                      ? location.pathname.startsWith("/employees")
                      : item.to.startsWith("/employee-development")
                        ? location.pathname.startsWith("/employee-development")
                        : item.to === "/admin/users"
                          ? location.pathname.startsWith("/admin/users")
                          : location.pathname === item.to ||
                            location.pathname.startsWith(`${item.to}/`);
                  return `sidebar__link${active ? " sidebar__link--active" : ""}`;
                }}
              >
                <HrModuleIcon icon={iconKey} size="lg" label={item.label} />
                <span>{item.label}</span>
              </NavLink>
            );
            if (item.to === "/employees") {
              return (
                <EmployeeNavGroup
                  key={`${item.to}-${item.label}`}
                  link={link}
                  allowSubnav={!railCollapsed}
                />
              );
            }
            if (item.to === "/employee-development/performance") {
              return (
                <EmployeeDevelopmentNavGroup
                  key={`${item.to}-${item.label}`}
                  link={link}
                  allowSubnav={!railCollapsed}
                  canManage={!selfService && hasPermission("employees", "read")}
                />
              );
            }
            if (item.to === "/admin/users") {
              return (
                <UserManagementNavGroup
                  key={`${item.to}-${item.label}`}
                  link={link}
                  allowSubnav={!railCollapsed}
                />
              );
            }
            return (
              <span key={`${item.to}-${item.label}`} className="sidebar__nav-item">
                {link}
              </span>
            );
          })}
        </nav>
        <div className="sidebar__footer">
          <div className="sidebar__user">
            <span className="sidebar__user-email">{user?.username || user?.email}</span>
            <span className="sidebar__user-roles font-data">{user?.roles.join(", ")}</span>
          </div>
          <Button
            variant="secondary"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            <LogOut size={18} aria-hidden />
            <span>Sign out</span>
          </Button>
          <p className="sidebar__credit">
            Made by Izaan Bin Mujeeb for Kafi Commodities
          </p>
        </div>
      </aside>
      <div className="shell__main">
        <div className="shell__chrome">
          {isMobile ? (
            <button
              type="button"
              className="sidebar__toggle sidebar__toggle--chrome"
              aria-label="Open menu"
              aria-expanded={mobileOpen}
              aria-controls="app-sidebar"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={20} aria-hidden />
            </button>
          ) : null}
          <div className="shell__chrome-end">
            <NotificationBell />
          </div>
        </div>
        <Outlet />
      </div>
    </div>
  );
}

function EmployeeNavGroup({
  link,
  allowSubnav,
}: {
  link: ReactNode;
  allowSubnav: boolean;
}) {
  const location = useLocation();
  const onEmployees = location.pathname.startsWith("/employees");
  const [open, setOpen] = useState(onEmployees);

  useEffect(() => {
    if (onEmployees) setOpen(true);
  }, [onEmployees]);

  useEffect(() => {
    if (!allowSubnav) setOpen(false);
  }, [allowSubnav]);

  return (
    <div className="sidebar__group">
      <div className="sidebar__link-row">
        {link}
        {allowSubnav ? (
          <button
            type="button"
            className={`sidebar__group-toggle${open ? " is-open" : ""}`}
            aria-expanded={open}
            aria-label={
              open ? "Collapse Employees Management menu" : "Expand Employees Management menu"
            }
            onClick={() => setOpen((value) => !value)}
          >
            <ChevronDown size={18} aria-hidden />
          </button>
        ) : null}
      </div>
      <EmployeeSectionMenus open={allowSubnav && open} />
    </div>
  );
}

function EmployeeDevelopmentNavGroup({
  link,
  allowSubnav,
  canManage,
}: {
  link: ReactNode;
  allowSubnav: boolean;
  canManage: boolean;
}) {
  const location = useLocation();
  const onSection = location.pathname.startsWith("/employee-development");
  const [open, setOpen] = useState(onSection);

  useEffect(() => {
    if (onSection) setOpen(true);
  }, [onSection]);

  useEffect(() => {
    if (!allowSubnav) setOpen(false);
  }, [allowSubnav]);

  return (
    <div className="sidebar__group">
      <div className="sidebar__link-row">
        {link}
        {allowSubnav ? (
          <button
            type="button"
            className={`sidebar__group-toggle${open ? " is-open" : ""}`}
            aria-expanded={open}
            aria-label={
              open ? "Collapse Employee Development menu" : "Expand Employee Development menu"
            }
            onClick={() => setOpen((value) => !value)}
          >
            <ChevronDown size={18} aria-hidden />
          </button>
        ) : null}
      </div>
      <EmployeeDevelopmentSectionMenus open={allowSubnav && open} canManage={canManage} />
    </div>
  );
}

function UserManagementNavGroup({
  link,
  allowSubnav,
}: {
  link: ReactNode;
  allowSubnav: boolean;
}) {
  const location = useLocation();
  const onSection = location.pathname.startsWith("/admin/users");
  const [open, setOpen] = useState(onSection);

  useEffect(() => {
    if (onSection) setOpen(true);
  }, [onSection]);

  useEffect(() => {
    if (!allowSubnav) setOpen(false);
  }, [allowSubnav]);

  return (
    <div className="sidebar__group">
      <div className="sidebar__link-row">
        {link}
        {allowSubnav ? (
          <button
            type="button"
            className={`sidebar__group-toggle${open ? " is-open" : ""}`}
            aria-expanded={open}
            aria-label={
              open ? "Collapse User Management menu" : "Expand User Management menu"
            }
            onClick={() => setOpen((value) => !value)}
          >
            <ChevronDown size={18} aria-hidden />
          </button>
        ) : null}
      </div>
      <UserManagementSectionMenus open={allowSubnav && open} />
    </div>
  );
}
