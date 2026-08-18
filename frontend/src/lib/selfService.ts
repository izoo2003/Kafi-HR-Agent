import { AGENT_KEY, PERMISSION_RANK } from "./case";
import type { AuthContextData } from "../types/common";

export function isSelfService(user: AuthContextData | null): boolean {
  if (!user?.linkedEmployeeId) return false;
  const level = user.agentPermissions[`${AGENT_KEY}.employees`] ?? "none";
  return (PERMISSION_RANK[level] ?? 0) < PERMISSION_RANK.read;
}

export function homePath(user: AuthContextData | null): string {
  if (!user) return "/login";
  const level = (moduleKey: string) =>
    PERMISSION_RANK[user.agentPermissions[`${AGENT_KEY}.${moduleKey}`] ?? "none"] ?? 0;
  if (level("admin_panel") >= PERMISSION_RANK.read) return "/admin/dashboard";
  if (level("attendance") >= PERMISSION_RANK.read) return "/attendance";
  if (level("kpi") >= PERMISSION_RANK.read) return "/kpi/dashboard";
  return "/not-authorized";
}
