import type { ReactNode } from "react";
import "./Card.css";

type Props = {
  children: ReactNode;
  status?: string;
  className?: string;
};

export function Card({ children, status, className = "" }: Props) {
  return (
    <div className={`card ${className}`.trim()} {...(status ? { "data-status": status } : {})}>
      {children}
    </div>
  );
}
