# INTEGRATION CONTRACT — HR & Admin Agent

> This is the spec for `backend/app/integration/interface.py` — the **only** module a future orchestrator or sibling agent (e.g. Utilities & Maintenance) is allowed to import from. Nothing else in this codebase is a stable external contract, and nothing in this codebase directly imports a sibling agent's internals either.

This agent runs **standalone today**. Every item below should be implemented as a real, working function/stub now, even though nothing calls it yet — so that plugging in an orchestrator later is a wiring change, not a rewrite.

---

## 1. Design Principles

1. **One door in, one door out.** All inbound calls from outside this agent go through `interface.py`. All outbound calls to sibling agents (once they exist) also go through a well-defined client in this same module — never a direct Python import of another agent's code.
2. **Typed everything.** Every function signature uses Pydantic models for input and output. No raw dicts crossing the boundary.
3. **Versioned contracts.** Every public function and event has a version tag. Breaking changes bump the version; old versions stay supported until the orchestrator confirms migration.
4. **Stateless where possible.** Interface functions should not assume in-memory state from a prior call — the orchestrator may call this agent from a different process.
5. **Fail loud, fail typed.** Interface functions raise well-defined exception types (see §5), never bare exceptions, so the orchestrator can handle failures predictably.
6. **No ownership of out-of-scope domains.** If a call would require kitchen/IT/generator/solar data, this agent returns a `NotOwnedByThisAgent` response pointing to the expected sibling agent key — it never fabricates or partially implements that logic.

---

## 2. Identity & Auth Context

The orchestrator (once it exists) will pass an **auth context** on every call — for now, this agent generates its own JWTs standalone, but the shape must already match what a shared identity provider would issue.

```python
class AuthContext(BaseModel):
    user_id: int
    email: str
    username: str | None = None
    roles: list[str]
    agent_permissions: dict[str, str]   # { "hr_admin.payroll": "approve", "hr_admin.kpi": "write", ... }
    source: Literal["standalone", "orchestrator"]  # tells this agent whether it minted the token itself
    linked_employee_id: int | None = None  # AUTH_AND_RBAC.md §6 — employee self-service row filter
    department_id: int | None = None  # from linked employee, for self-service UI
```


- Today: `source = "standalone"`, token minted and validated by this agent's own `/auth` routes.
- Later: `source = "orchestrator"`, token minted by shared identity provider, this agent only validates signature + maps `agent_permissions`.
- The permission-checking code path must be identical either way — this is what "aligned with the shared user role matrix" means in practice (see `AUTH_AND_RBAC.md`).

---

## 3. Public Functions (`interface.py`)

All functions below are the *complete* current surface. Add new ones here first, in this doc, before implementing.

### 3.1 Capability Discovery

```python
def get_capabilities() -> AgentCapabilities:
    """Returns this agent's key, version, modules, and events. 
    Orchestrator calls this on registration to know what this agent can do."""
```

```python
class AgentCapabilities(BaseModel):
    agent_key: str = "hr_admin"
    version: str
    modules: list[str]   # ["job_descriptions", "cv_screening", "attendance", "payroll", "kpi", "admin_panel"]
    events_emitted: list[str]
    events_consumed: list[str]
```

### 3.2 Health

```python
def health_check() -> HealthStatus:
    """Liveness/readiness for orchestrator monitoring."""

class HealthStatus(BaseModel):
    status: Literal["ok", "degraded", "down"]
    db_connected: bool
    details: str | None = None
```

### 3.3 Employee Directory Lookup (read-only, likely consumed by sibling agents)

```python
def get_employee_summary(employee_id: int, auth: AuthContext) -> EmployeeSummary | None:
    """Minimal, non-sensitive employee info for sibling agents 
    (e.g. Utilities agent tagging an IT asset to an employee)."""

class EmployeeSummary(BaseModel):
    employee_id: int
    full_name: str
    department: str
    status: Literal["active", "on_leave", "terminated"]
```

Note: deliberately excludes salary, KPI, and personal data — sibling agents get identity/org data only, never HR-sensitive fields, unless a future explicit contract says otherwise.

### 3.4 Permission Check (used by orchestrator to gate UI/routes before calling this agent)

```python
def check_permission(auth: AuthContext, module_key: str, action: str) -> bool:
    """module_key e.g. 'payroll', action e.g. 'approve'."""
```

### 3.5 Audit Event Emission (outbound — this agent tells the orchestrator what happened)

```python
def emit_audit_event(event: AuditEvent) -> None:
    """Called internally whenever a write happens. Today: writes to local audit_logs table only.
    Later: also publishes to shared orchestrator event bus."""

class AuditEvent(BaseModel):
    agent_key: str = "hr_admin"
    action: str              # "payroll.approve", "cv.score_override", etc.
    entity_type: str
    entity_id: int
    user_id: int
    timestamp: datetime
```

### 3.6 Out-of-Scope Routing (stub)

```python
def route_to_sibling_agent(request: SiblingAgentRequest) -> SiblingAgentResponse:
    """Stub/no-op today. Once orchestrator exists, forwards requests for 
    kitchen/IT/generator/solar data to the Utilities & Maintenance agent."""

class SiblingAgentRequest(BaseModel):
    target_agent_key: str    # e.g. "utilities_maintenance"
    action: str
    payload: dict

class SiblingAgentResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None
```

Until the orchestrator exists, any internal code path that would need this returns `NotOwnedByThisAgent` (see §5) instead of calling this stub — the stub exists so the *signature* is stable, not so it's exercised yet.

---

## 4. Events

Events are how this agent will eventually communicate asynchronously with the orchestrator and siblings. Today they are logged locally (via `emit_audit_event` and equivalents); later they'll be published to a real bus (exact transport TBD by whoever builds the orchestrator — this agent should not assume Kafka vs Redis vs webhook, keep the publishing call abstracted behind one function).

### Events Emitted by This Agent

| Event Name | Payload Shape | When |
|---|---|---|
| `hr_admin.employee.created` | `EmployeeSummary` | New employee record created |
| `hr_admin.employee.exited` | `{ employee_id, date_exited }` | Employee marked exited |
| `hr_admin.payroll.run_approved` | `{ payroll_run_id, period_month, period_year }` | Payroll run approved |
| `hr_admin.candidate.hired` | `{ candidate_id, job_description_id, employee_id }` | Candidate converted to employee |
| `hr_admin.kpi.period_closed` | `{ department_id, period_start, period_end }` | KPI review period finalized |

### Events This Agent Would Consume (future, from sibling agents / orchestrator)

| Event Name | Expected Source | Why This Agent Cares |
|---|---|---|
| `orchestrator.user.role_changed` | Orchestrator | Sync local role cache if identity becomes centralized |
| `utilities.asset.assigned_to_employee` | Utilities & Maintenance agent | Could surface in employee profile as read-only info (future, not built now) |

Consumption is **not implemented now** — this table documents intent so the interface doesn't need restructuring when it is.

---

## 5. Exceptions / Error Contract

```python
class HrAdminAgentError(Exception):
    """Base class for all interface-boundary errors."""

class NotOwnedByThisAgent(HrAdminAgentError):
    """Raised when a request concerns an out-of-scope domain 
    (kitchen, IT, generator, solar). Includes expected_agent_key."""
    expected_agent_key: str = "utilities_maintenance"

class PermissionDenied(HrAdminAgentError):
    pass

class EntityNotFound(HrAdminAgentError):
    pass

class InvalidAuthContext(HrAdminAgentError):
    pass
```

The orchestrator (and this agent's own API layer) should catch these and map to the HTTP error codes in `API_ENDPOINTS.md` §11.

---

## 6. Registry Stub

```python
# integration_registry table, see DATABASE_SCHEMA.md §8
def register_with_orchestrator(orchestrator_url: str | None = None) -> RegistrationResult:
    """No-op today — returns status='standalone'. 
    Once an orchestrator exists, performs actual registration handshake."""

class RegistrationResult(BaseModel):
    status: Literal["standalone", "registered", "failed"]
    agent_key: str = "hr_admin"
    message: str | None = None
```

---

## 7. What NOT to Do

- Do not let any file outside `app/integration/` be imported by anything outside this codebase.
- Do not implement real kitchen/IT/generator/solar logic anywhere, even "temporarily," to unblock a feature — raise `NotOwnedByThisAgent` instead and surface it to the user/admin.
- Do not hardcode assumptions that this is the only agent running (e.g. don't assume `user_id` uniqueness is scoped only to this DB if identity becomes shared later — keep `AuthContext.source` checks in place).
- Do not pick a message-bus technology inside module code — all event publishing goes through the one abstracted function in `interface.py` so the transport can be swapped later without touching business logic.

---

## 8. Change Log Discipline

Any change to a function signature, event payload, or exception type in this file must be reflected here **and** in `interface.py` in the same commit/session. This doc is not documentation-after-the-fact — it is the spec Cursor should write code against.
