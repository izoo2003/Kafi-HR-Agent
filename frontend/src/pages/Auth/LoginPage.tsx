import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { ApiError } from "../../api/client";
import { homePath } from "../../lib/selfService";
import "./LoginPage.css";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!loading && user) {
    return <Navigate to={from && from !== "/login" ? from : homePath(user)} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate(from && from !== "/login" ? from : "/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Invalid username or PIN.");
      } else {
        setError("Unable to sign in. Check that the API is running.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login">
      <form className="login__card" onSubmit={onSubmit}>
        <div className="login__brand">
          <span className="login__mark">K</span>
          <div>
            <h1>Kafi HR Admin</h1>
            <p>Sign in with your username and PIN</p>
          </div>
        </div>
        <FormField
          label="Username or email"
          type="text"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          hint="Staff can still use their email address."
        />
        <FormField
          label="PIN or password"
          type="password"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          error={error ?? undefined}
        />
        <Button type="submit" variant="primary" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
