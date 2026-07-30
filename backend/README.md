# Backend — HR & Admin Agent

FastAPI backend aligned with `docs/BACKEND_ARCHITECTURE.md` and `docs/AUTH_AND_RBAC.md`.

## Layout

```
app/
  core/           # config, db, security, deps, exceptions
  models/         # SQLAlchemy models (DATABASE_SCHEMA.md)
  schemas/        # Pydantic request/response
  services/       # business logic + seeds
  api/routes/     # /api/v1 routers
  integration/    # public interface.py + event bus stub
  ingestion/ parsing/ scoring/ ranking/ reporting/ pipeline.py
alembic/          # migrations
_legacy_phase1/   # archived Phase-1 Gmail pipeline (reference only)
```

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`: set `JWT_SECRET_KEY` and optionally `SEED_ADMIN_*`.

## Run

```powershell
python main.py
```

- API: http://127.0.0.1:8808
- Docs: http://127.0.0.1:8808/docs
- Health: http://127.0.0.1:8808/health

### First login (seeded on boot)

- Email: value of `SEED_ADMIN_EMAIL` (default `admin@kafi-group.com`)
- Password: value of `SEED_ADMIN_PASSWORD` (default `ChangeMeAdmin123!`)

```http
POST /api/v1/auth/login
{ "email": "admin@kafi-group.com", "password": "ChangeMeAdmin123!" }
```

Then call protected routes with `Authorization: Bearer <access_token>`.

## Migrations

On startup in development, `create_all` + seed run automatically.
For Alembic:

```powershell
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

## What’s scaffolded vs full features

| Area | Status |
|------|--------|
| Auth JWT + RBAC matrix | Working |
| All DB tables | Created |
| Integration interface stubs | Working |
| Module routes (JD/CV/attendance/payroll/KPI) | Placeholders until feature `.md` packs |
| CV/Gmail Phase-1 pipeline | Moved to `_legacy_phase1/` |
