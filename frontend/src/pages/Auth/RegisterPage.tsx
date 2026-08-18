import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { ApiError } from "../../api/client";
import { getRegisterOptions } from "../../api/auth";
import { homePath } from "../../lib/selfService";
import "./LoginPage.css";

export function RegisterPage() {
  const { user, loading, register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [pinConfirm, setPinConfirm] = useState("");
  const [departmentId, setDepartmentId] = useState<number | "">("");
  const [departments, setDepartments] = useState<{ id: number; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getRegisterOptions()
      .then((res) => {
        if (!cancelled) setDepartments(res.departments ?? []);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? `Could not load departments: ${err.message}`
              : "Could not load departments. Check that the API is running.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!loading && user) {
    return <Navigate to={homePath(user)} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (departmentId === "") {
      setError("Select your department.");
      return;
    }
    if (pin !== pinConfirm) {
      setError("PINs do not match.");
      return;
    }
    if (!/^\d{4,8}$/.test(pin)) {
      setError("PIN must be 4–8 digits.");
      return;
    }
    setSubmitting(true);
    try {
      await register({
        fullName: fullName.trim(),
        username: username.trim(),
        pin,
        departmentId,
      });
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Could not create account.");
      } else {
        setError("Unable to register. Check that the API is running.");
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
            <h1>Create your account</h1>
            <p>Choose a username and PIN to track your attendance and KPIs</p>
          </div>
        </div>
        <FormField
          label="Full name"
          name="fullName"
          autoComplete="name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />
        <FormField
          label="Username"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          hint="Letters, numbers, dots, underscores, or hyphens."
        />
        <label className="form-field">
          <span className="form-field__label">Department</span>
          <select
            className="form-field__input"
            required
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select…</option>
            {(departments ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <FormField
          label="PIN (4–8 digits)"
          type="password"
          name="pin"
          inputMode="numeric"
          autoComplete="new-password"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          required
        />
        <FormField
          label="Confirm PIN"
          type="password"
          name="pinConfirm"
          inputMode="numeric"
          autoComplete="new-password"
          value={pinConfirm}
          onChange={(e) => setPinConfirm(e.target.value)}
          required
          error={error ?? undefined}
        />
        <Button type="submit" variant="primary" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </Button>
        <p className="login__footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
