# Backend — HR & Admin Agent (Phase 1: CV Ranking)

Python backend. Ingests candidate CVs from Gmail and a Google Form, scores
them against role-specific criteria using Gemini, ranks them per position,
and produces HR-friendly formatted Excel reports (overview ranking table +
detailed candidate profiles) — same structure as the reference ranking
report. Exposes both a CLI and a REST API (consumed by `../frontend`).

WhatsApp intake (+92 333 0313518) is stubbed for a later phase; see
`app/ingestion/whatsapp_ingestor.py`.

## Project structure

```
app/
  config.py                 # loads .env + config/*.yaml
  db/                        # SQLite models (Candidate, Application) + session
  ingestion/                 # gmail_ingestor, google_form_ingestor, whatsapp_ingestor (stub)
  parsing/cv_parser.py       # PDF/DOCX -> plain text
  scoring/                   # rubric-driven Gemini scoring
  ranking/ranker.py          # groups by position, assigns rank
  reporting/excel_report.py  # formatted .xlsx report generation
  integration/interface.py  # PUBLIC seam for the future multi-agent orchestrator
  pipeline.py                # orchestrates fetch -> score -> rank -> report
  cli.py                     # command-line interface
  api/                       # FastAPI app consumed by the frontend
    main.py                  # app instance, CORS, router registration
    schemas.py                # request/response models (Pydantic)
    deps.py                   # shared FastAPI dependencies (DB session)
    routes/                   # positions.py, pipeline.py, reports.py
config/
  scoring_rubric.yaml        # weighted rubric + verdict bands (85+/70+/55+/<55)
  roles.yaml                 # per-role required/nice-to-have skills (extend as roles are added)
docs/
  google_form_field_spec.md  # exact fields to create in the Google Form
data/
  cv_files/                  # downloaded CVs land here
  reports/                   # generated Excel reports land here
  hr_agent.db                # SQLite database (created on first run)
credentials/                 # OAuth client + tokens (gitignored, not committed)
```

## One-time setup

### 1. Python environment

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Gemini API key

1. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.

### 3. Google Cloud project (for Gmail + Sheets/Drive access)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create/select a project.
2. Enable APIs: **Gmail API**, **Google Sheets API**, **Google Drive API**.
3. Configure the OAuth consent screen (External is fine for testing; add `hr@kafi-group.com` as a test user if the app stays in "Testing" mode).
4. Create an **OAuth client ID** → Application type: **Desktop app**.
5. Download the JSON, save it as `credentials/google_oauth_client.json`.
6. In `.env`, confirm `GOOGLE_OAUTH_CREDENTIALS_FILE=credentials/google_oauth_client.json`.

The first time Gmail or Google Form ingestion runs, a browser window opens
for you to sign in as `hr@kafi-group.com` and grant access. After that,
tokens are cached in `credentials/` and refresh silently.

### 4. Google Form (CV submissions)

Follow `docs/google_form_field_spec.md` to create the form and link it to a
Google Sheet. Then put that Sheet's ID into `.env` as
`GOOGLE_FORM_RESPONSES_SHEET_ID` (the long ID in the sheet's URL between
`/d/` and `/edit`).

### 5. Initialize the database

```powershell
python -m app.cli init-db
```

## Running

### Option A — REST API (for the frontend dashboard)

```powershell
.venv\Scripts\activate
python main.py
```

- API docs (Swagger UI): http://127.0.0.1:8808/docs
- Health check: http://127.0.0.1:8808/health

### Option B — CLI (scriptable / cron-friendly, no server needed)

```powershell
python main.py cli fetch --source gmail
python main.py cli score
python main.py cli rank
python main.py cli report
python main.py cli run-all
```

Or equivalently: `python -m app.cli <command>`

Both paths share the exact same underlying pipeline (`app/pipeline.py`) — the
API just wraps it in HTTP endpoints for the dashboard, and also lets you
trigger fetch/score/rank/report + download reports from the browser.

Reports land in `data/reports/`:
- `CV_Ranking_<Position>_<date>.xlsx` — per position, Overview + Detailed Profiles sheets
- `CV_Ranking_Master_<date>.xlsx` — one row per position, for a quick admin scan

## Scoring model

- `config/scoring_rubric.yaml` — weights (experience 30%, skill match 25%, education 15%, measurable impact 15%, certifications 10%, CV clarity 5%) and the 4 verdict bands (STRONG HIRE / RECOMMEND / CONDITIONAL / NOT RECOMMENDED), same bands as the reference report.
- `config/roles.yaml` — per-role required/nice-to-have skills and minimum experience. Add a new entry per open role as job descriptions are finalized (scope item 1); anything not yet profiled falls back to the generic `default` profile so nothing breaks.
- The verdict label is always computed locally from the score against the bands above — the LLM only supplies the score and narrative, never the label, so bands stay consistent even if the model's wording drifts.

## Multi-agent integration

This module is designed to plug into a future shared orchestrator without a
rewrite (see the always-applied Cursor rule `hr-admin-agent.mdc`):

- **`app/integration/interface.py`** is the only file a parent agent or
  sibling agent should ever import from — typed request/response
  dataclasses (`RunPipelineResponse`, `CandidateRankingDTO`), an `AuthContext`
  stub that will carry identity/permissions from the shared user role matrix
  once that exists, and a no-op `subscribe`/`_emit` event hook seam.
- Everything else (`db`, `ingestion`, `scoring`, `ranking`, `reporting`, `api`)
  is a private implementation detail and can be refactored freely as long as
  `interface.py`'s signatures stay stable.
