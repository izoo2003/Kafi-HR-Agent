# AUTH & RBAC — HR & Admin Agent

> How authentication and role-based access control work end to end: login, token shape, permission checks, and how this stays aligned with the shared user role matrix so it merges cleanly into a future orchestrator. Read alongside `DATABASE_SCHEMA.md` §1 (identity tables) and `INTEGRATION_CONTRACT.md` §2 (`AuthContext`).

---

## 1. Roles (default seed set)

Seeded via migration, editable later through `/roles` and `/access-matrix` endpoints. This list is a starting point, not hardcoded logic — permission checks must never `if role == "hr_manager"` in code; they must always check the `agent_access_matrix` table.

| Role | Intended For |
|---|---|
| `super_admin` | Full access to everything, including admin panel and system config |
| `hr_manager` | Full access to CV screening, employees, KPI; read/approve on payroll |
| `payroll_officer` | Full access to payroll, read-only elsewhere |
| `department_head` | Read on their department's employees/KPI/attendance, approve leave requests for their team |
| `recruiter` | Full access to job descriptions & CV screening only |
| `employee` | Self-service: own attendance, own KPIs (create/record), own payslips |
| `readonly_auditor` | Read-only across all modules, including audit logs — no writes anywhere |

---

## 2. Permission Model

Two layers, both backed by DB tables (never hardcoded):

1. **Module-level (coarse):** `agent_access_matrix` — per role, per `agent_key` + `module_key`, one of `none | read | write | approve | admin`. This is the **user role matrix** referenced as in-scope item 6 in `PROJECT_OVERVIEW.md`, and it's designed so that adding a second `agent_key` row (for a sibling agent) later requires zero schema change.

2. **Action-level (fine-grained, optional):** `permissions` + `role_permissions` — specific codes like `payroll.approve`, `cv.override_score`, used where module-level granularity (`write` vs `approve`) isn't precise enough. Use sparingly; prefer module-level checks unless a route genuinely needs a distinct gate from plain `write`.

**Resolution order when checking access:**
1. Is the user's token valid and not expired?
2. Does any of the user's roles have `module_key` permission ≥ the level required by this route (`read` < `write` < `approve` < `admin`)?
3. If the route also requires a fine-grained permission code, does any of the user's roles have that code?
4. If both checks pass → allowed. Otherwise → `403 forbidden`.

---

## 3. Token Shape

JWT access token claims:

```json
{
  "sub": "<user_id>",
  "email": "user@example.com",
  "roles": ["hr_manager"],
  "iat": 1234567890,
  "exp": 1234571490,
  "source": "standalone"
}
```

- Short-lived access token (e.g. 30 min) + longer-lived refresh token (e.g. 7 days), refresh token stored httpOnly cookie or secure storage per frontend convention in `FRONTEND_ARCHITECTURE.md`.
- `roles` in the token are a snapshot at login time — the actual permission check on each request re-resolves current `agent_access_matrix` state from DB (via `roles` → matrix lookup), so a role's permissions changing takes effect without forcing re-login. Only role *assignment* changes require re-login (or a refresh-triggered re-check).
- `source` field: `"standalone"` today, reserved for `"orchestrator"` once a shared identity provider exists — see `INTEGRATION_CONTRACT.md` §2. Token validation logic must branch on this only for *where the signing key comes from*, never for *how permissions are computed* — permission computation is identical either way.

---

## 4. FastAPI Dependency Chain

Implemented in `app/core/deps.py`, used by every protected route:

```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AuthContext:
    """Decode JWT, verify signature/expiry, load user + roles from DB, 
    resolve agent_access_matrix into AuthContext.agent_permissions dict."""

def require_permission(module_key: str, min_level: str):
    """Returns a FastAPI dependency that raises PermissionDenied (-> 403) 
    if current AuthContext doesn't meet min_level for module_key."""
```

Usage in a route:

```python
@router.post("/payroll-runs/{id}/approve")
def approve_payroll_run(
    id: int,
    auth: AuthContext = Depends(require_permission("payroll", "approve")),
    db: Session = Depends(get_db),
):
    ...
```

This keeps every route's permission requirement visible and declarative right in the route signature — Cursor (or any reviewer) can see the required access level without reading the service body.

---

## 5. Frontend Role Awareness

- On login, `/auth/me` returns the full resolved `AuthContext` (roles + `agent_permissions` map).
- Stored in a React context (`AuthContext` provider — see `FRONTEND_ARCHITECTURE.md`), consumed by:
  - Route guards (hide/redirect pages the user has no `read` access to).
  - Conditional rendering of write/approve actions (e.g. hide "Approve" button unless `agent_permissions["hr_admin.payroll"] === "approve"`).
- **Frontend checks are UX only, never security.** Every backend route independently re-checks permission — the frontend hiding a button is not a substitute for the `require_permission` dependency.

---

## 6. Employee Self-Service Boundary

The `employee` role is a special case: employees see **only their own** records (their attendance, their payslips, their KPI scores), not module-wide `read` access. This is enforced via row-level filtering in the service layer, not the module-level matrix alone:

- Service functions for self-service callers (linked employee + no `employees` module read) must filter `WHERE employee_id = auth.linked_employee_id` regardless of what the route's general query params say.
- Public signup (`POST /auth/register`) creates a user with a unique `username` + hashed PIN, assigns the `employee` role, and creates a linked `employees` row so `linked_employee_id` is set immediately.
- Login accepts **username or email** plus PIN/password (`POST /auth/login`).
- Self-service users may create **personal** KPI definitions (`kpi_definitions.owner_employee_id`) and record actuals against those (and department KPIs), still scoped to themselves.

---

## 7. Audit Trail for Auth/Access Changes

Per `DATABASE_SCHEMA.md` §7 and `FEATURE_AUDIT_LOG.md`, these are always logged:

- Login success/failure
- Role assigned/removed from a user
- `agent_access_matrix` entry changed
- Password reset/changed
- Score override, payroll approval, or any other action gated by `approve`/`admin` level

---

## 8. Alignment With Future Orchestrator

- This agent's `roles` and `agent_access_matrix` tables are designed to be **the seed of** a shared identity system, not a throwaway local scheme that gets replaced. When an orchestrator exists:
  - `agent_key` column already supports multiple agents per row.
  - `AuthContext.source` flips to `"orchestrator"`; token signing moves to a shared identity provider; permission *resolution logic* (module_key/min_level checks) does not change.
  - No route code changes — only where `get_current_user` sources the token verification key.
- Test question for any auth-related change: *"If this agent's users/roles get merged into a shared identity table tomorrow, does this still work?"* If a check hardcodes an assumption that this agent's `user_id` space is globally unique or that no other agent's roles exist, flag it before implementing.
