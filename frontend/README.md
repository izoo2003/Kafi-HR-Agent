# Frontend — HR & Admin Agent Dashboard

React + Vite + TypeScript admin UI aligned with:
- `docs/FRONTEND_ARCHITECTURE.md`
- `docs/UI_DESIGN_SYSTEM.md`

Talks to the backend only via `/api/v1` (`VITE_API_BASE_URL`). Never imports backend code.

## Structure

```
src/
  pages/{Module}/     # route pages
  components/ui/      # Button, Table, Badge, Card, …
  components/layout/  # AppShell, RequirePermission
  components/domain/  # HR-aware shared widgets (add as features land)
  api/                # one file per backend module
  hooks/              # React Query wrappers
  context/            # AuthContext
  types/              # camelCase mirrors of backend schemas
  styles/tokens.css   # design tokens
  constants/          # status label vocabulary
```

## Setup

```powershell
cd frontend
npm install
copy .env.example .env
```

## Run

Backend must be on port **8808** first.

```powershell
npm run dev
```

Open http://localhost:5288 — sign in with seed admin from backend `.env`.

## Auth & permissions

- Login → JWT stored in localStorage → `/auth/me` populates `AuthContext`
- Sidebar + routes gated with `RequirePermission` using the same `module` / `level` vocabulary as the backend
- Frontend checks are UX only; backend re-checks every request
