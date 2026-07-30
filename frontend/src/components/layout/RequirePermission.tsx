import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import type { PermissionLevel } from "../../types/common";
import { Spinner } from "../ui/Spinner";

export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div style={{ padding: "var(--space-8)" }}>
        <Spinner label="Checking session" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

type Props = {
  module: string;
  level?: PermissionLevel;
};

export function RequirePermission({ module, level = "read" }: Props) {
  const { hasPermission, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ padding: "var(--space-8)" }}>
        <Spinner label="Checking permissions" />
      </div>
    );
  }
  if (!hasPermission(module, level)) {
    return <Navigate to="/not-authorized" replace />;
  }
  return <Outlet />;
}
