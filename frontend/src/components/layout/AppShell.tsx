import { NavLink, Outlet, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import {
  BriefcaseBusiness,
  ClipboardList,
  FileSpreadsheet,
  Gauge,
  LayoutDashboard,
  LogOut,
  UserRound,
  Users,
  Wallet,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { Button } from "../ui/Button";
import { NotificationBell } from "./NotificationBell";
import "./AppShell.css";

const NAV = [
  { to: "/admin/dashboard", label: "Admin", module: "admin_panel", icon: LayoutDashboard },
  { to: "/employees", label: "Employees", module: "employees", icon: UserRound },
  { to: "/job-descriptions", label: "Job Postings", module: "job_descriptions", icon: BriefcaseBusiness },
  { to: "/cv-screening", label: "CV Screening", module: "cv_screening", icon: ClipboardList },
  { to: "/attendance", label: "Attendance", module: "attendance", icon: FileSpreadsheet },
  { to: "/payroll/runs", label: "Payroll", module: "payroll", icon: Wallet },
  { to: "/kpi/dashboard", label: "KPI", module: "kpi", icon: Gauge },
  { to: "/admin/users", label: "Users", module: "users", icon: Users },
] as const;

type ShellProps = {
  title: string;
  breadcrumb?: string;
  actions?: ReactNode;
};

export function PageHeader({ title, breadcrumb, actions }: ShellProps) {
  return (
    <header className="topbar">
      <div>
        {breadcrumb ? <p className="topbar__crumb">{breadcrumb}</p> : null}
        <h1 className="topbar__title">{title}</h1>
      </div>
      {actions ? <div className="topbar__actions">{actions}</div> : null}
    </header>
  );
}

export function AppShell() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__brand-mark">K</span>
          <div>
            <strong>Kafi HR</strong>
            <span>Admin Agent</span>
          </div>
        </div>
        <nav className="sidebar__nav" aria-label="Modules">
          {NAV.filter((item) => hasPermission(item.module, "read")).map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={`${item.to}-${item.label}`}
                to={item.to}
                className={({ isActive }) =>
                  `sidebar__link${isActive ? " sidebar__link--active" : ""}`
                }
              >
                <Icon size={18} strokeWidth={1.75} aria-hidden />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar__footer">
          <div className="sidebar__user">
            <span className="sidebar__user-email">{user?.email}</span>
            <span className="sidebar__user-roles font-data">{user?.roles.join(", ")}</span>
          </div>
          <Button
            variant="secondary"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            <LogOut size={16} aria-hidden /> Sign out
          </Button>
          <p className="sidebar__credit">
            Made by Izaan Bin Mujeeb for Kafi Commodities
          </p>
        </div>
      </aside>
      <div className="shell__main">
        <div className="shell__utility">
          <NotificationBell />
        </div>
        <Outlet />
      </div>
    </div>
  );
}
