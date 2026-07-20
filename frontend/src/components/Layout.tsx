import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <Link to="/" className="app-title">
            HR &amp; Admin Agent
          </Link>
          <span className="app-subtitle">CV Ranking</span>
        </div>
      </header>
      <main className="app-content">{children}</main>
    </div>
  );
}
