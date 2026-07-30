import type { ReactNode } from "react";
import "./Badge.css";

type Props = {
  status: string;
  children: ReactNode;
};

export function StatusBadge({ status, children }: Props) {
  return (
    <span className="status-badge" data-badge-status={status}>
      {children}
    </span>
  );
}
