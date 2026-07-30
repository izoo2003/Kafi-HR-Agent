import { PageHeader } from "../components/layout/AppShell";
import { EmptyState } from "../components/ui/EmptyState";
import { Button } from "../components/ui/Button";
import { useNavigate } from "react-router-dom";

export function NotAuthorizedPage() {
  const navigate = useNavigate();
  return (
    <>
      <PageHeader title="Not authorized" />
      <div className="page">
        <EmptyState
          title="You don't have access to this module"
          description="Your role does not include read permission for this area. Ask an admin to update the access matrix if you need it."
          actionLabel="Go to dashboard"
          onAction={() => navigate("/admin/dashboard")}
        />
      </div>
    </>
  );
}

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="page" style={{ paddingTop: "var(--space-8)" }}>
      <EmptyState
        title="Page not found"
        description="That route does not exist in the HR Admin Agent."
        actionLabel="Back to dashboard"
        onAction={() => navigate("/")}
      />
      <div style={{ marginTop: "var(--space-4)" }}>
        <Button variant="secondary" onClick={() => navigate(-1)}>
          Go back
        </Button>
      </div>
    </div>
  );
}
