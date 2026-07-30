import type { ReactNode } from "react";
import { StatusBadge } from "../ui/Badge";

/** Domain wrapper so pages share one status→badge mapping entry point. */
export function DomainStatusBadge({
  status,
  children,
}: {
  status: string;
  children: ReactNode;
}) {
  return <StatusBadge status={status}>{children}</StatusBadge>;
}
