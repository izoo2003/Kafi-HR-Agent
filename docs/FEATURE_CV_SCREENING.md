# FEATURE: CV SCREENING — HR & Admin Agent

> Covers in-scope items 1 & 2 (Job Descriptions, CV Scoring Criteria). Read alongside `DATABASE_SCHEMA.md` §3, `API_ENDPOINTS.md` §4–5, `BACKEND_ARCHITECTURE.md` (`ingestion/`, `parsing/`, `scoring/`, `ranking/`, `reporting/`, `pipeline.py`).

---

## 1. End-to-End Flow

```
1. HR/Recruiter creates Job Description
2. HR/Recruiter defines Scoring Criteria for that role
3. HR/Recruiter (or bulk import) uploads Candidate CVs against that job
4. System parses each CV into structured fields
5. System scores each candidate against the job's criteria
6. System ranks all candidates for the job
7. HR reviews ranked list, can manually override a score (with reason, audit-logged)
8. HR shortlists/rejects candidates
9. HR exports ranking/shortlist report (PDF/Excel)
10. On hire, candidate converts to an Employee record (emits `hr_admin.candidate.hired`)
```

Steps 4–6 run as one pipeline call (`pipeline.run_cv_pipeline`) triggered automatically after upload, and re-triggerable manually via `/candidates/{id}/parse`, `/candidates/{id}/score`, `/job-descriptions/{id}/rank` for corrections.

---

## 2. Job Descriptions

- **Fields:** title, department, description text, requirements text, status (`draft`/`open`/`closed`), optional source file (Word/PDF upload used to pre-fill text, stored as-is).
- **Export:** `/job-descriptions/{id}/export` generates a formatted Word or PDF using `reporting/word_export.py` / `pdf_export.py`, populated from the structured fields (not a re-upload of the original file) — so edits made in-app are reflected in the export.
- **Status lifecycle:** `draft` → `open` (visible for CV intake) → `closed` (no new candidates accepted, existing candidates remain visible/scored).

---

## 3. Scoring Criteria — Rule Schema

Each `ScoringCriteria` row has a `scoring_rules` JSON field. This section fixes its shape so parsing/scoring code and the frontend criteria-builder UI agree on structure.

```json
{
  "type": "keyword_match" | "threshold_numeric" | "level_match" | "manual_review",
  "config": { ... }
}
```

### `keyword_match` (e.g. required skills)
```json
{
  "type": "keyword_match",
  "config": {
    "keywords": ["Python", "FastAPI", "PostgreSQL"],
    "match_mode": "any" | "all",
    "points_per_match": 5,
    "max_points": 15
  }
}
```

### `threshold_numeric` (e.g. years of experience)
```json
{
  "type": "threshold_numeric",
  "config": {
    "field": "years_experience",
    "bands": [
      { "min": 0, "max": 1, "points": 0 },
      { "min": 2, "max": 4, "points": 10 },
      { "min": 5, "max": null, "points": 20 }
    ]
  }
}
```

### `level_match` (e.g. education level)
```json
{
  "type": "level_match",
  "config": {
    "field": "education_level",
    "levels": { "bachelors": 10, "masters": 15, "phd": 20 },
    "below_minimum_points": 0,
    "minimum_required": "bachelors"
  }
}
```

### `manual_review` (e.g. portfolio quality — not machine-scorable)
```json
{
  "type": "manual_review",
  "config": {
    "instructions": "Reviewer scores portfolio quality 0-20 based on attached work samples.",
    "max_points": 20
  }
}
```
Manual review criteria produce a `CandidateScore` row with `raw_score = null` until a reviewer submits a score via the candidate detail page — these candidates show as "pending manual review" in the ranking until all `manual_review` criteria are scored.

**Total weighting:** `ScoringCriteria.weight` (a float, e.g. 0.3) is applied to the criterion's normalized 0–1 score (raw_score / max_points_for_that_rule_type) to produce its contribution to `CandidateRanking.total_score`. Weights across all criteria for one job description should be validated (frontend + backend) to sum to 1.0 at criteria-save time — reject with `validation_error` if not.

---

## 4. CV Parsing (`parsing/cv_parser.py`)

**Input:** file path (PDF or DOCX) from `Candidate.cv_file_path`.
**Output:** the `parsed_data` JSON shape stored on `Candidate`:

```json
{
  "full_name": "string | null",
  "email": "string | null",
  "phone": "string | null",
  "education": [
    { "degree": "string", "field": "string", "institution": "string", "year": "int | null", "level": "bachelors|masters|phd|diploma|other" }
  ],
  "experience": [
    { "title": "string", "company": "string", "start_date": "string|null", "end_date": "string|null", "description": "string" }
  ],
  "years_experience": "float",
  "skills": ["string"],
  "raw_text": "string"
}
```

- `years_experience` is computed from the experience date ranges, not just extracted as a stated number — this feeds `threshold_numeric` criteria directly.
- `raw_text` is retained for `keyword_match` scoring to run directly against full text as a fallback when `skills` extraction misses something, and for future re-scoring if criteria change without re-uploading.
- Parsing failures set `Candidate.status = "uploaded"` (not advanced to `"parsed"`) and surface an error the HR user can see, with an option to manually fill fields and proceed.

---

## 5. Scoring Engine (`scoring/cv_scorer.py`)

For each `ScoringCriteria` on the job:
1. Load the rule via `scoring_rules.type`.
2. Evaluate against `Candidate.parsed_data`.
3. Write a `CandidateScore` row (`raw_score`, plus `notes` if the rule flags something like "keyword not found, check raw_text manually").
4. Sum `weight * normalized_score` across all criteria → this becomes the candidate's total, written to `CandidateRanking.total_score` after the ranking step runs.

Manual override (`/candidates/{id}/score-override`): writes directly to a `CandidateScore` row's `raw_score` (or adds an adjustment), requires a `reason` string in the request body, always audit-logged with before/after state — this is a common regulated pattern in hiring so it must never be silent.

---

## 6. Ranking (`ranking/candidate_ranker.py`)

- Triggered automatically after scoring, and manually via `/job-descriptions/{id}/rank`.
- Pulls all candidates for the job with `status IN ("scored", "shortlisted", "rejected")`, computes `total_score`, orders descending, writes `rank_position` 1..N to `CandidateRanking`.
- Candidates with unresolved `manual_review` criteria still get a `total_score` (using only the resolved criteria's weighted contribution) but are visually flagged "pending manual review" in the frontend so HR doesn't mistake a partial score for a final one.

---

## 7. Candidate Status Lifecycle

```
uploaded → parsed → scored → (shortlisted | rejected) → hired
```

- `shortlisted`/`rejected` are manual HR actions (`PATCH /candidates/{id}`), not automatic — scoring informs the decision, doesn't make it.
- `hired` is set when an employee record is created from this candidate (a dedicated action, likely `POST /candidates/{id}/hire` — add to `API_ENDPOINTS.md` in the same session this route is implemented — that creates the `Employee` row and emits `hr_admin.candidate.hired` per `INTEGRATION_CONTRACT.md` §4).

---

## 8. Reporting

- `/job-descriptions/{id}/report` exports the current ranking as PDF (formatted list, top-N highlighted) or Excel (full data dump including per-criterion scores, useful for HR to sanity-check the rubric).
- Export always includes the scoring criteria weights used, so a report is self-explanatory to someone reviewing it later without needing to check the app.

---

## 9. Frontend Pages (see `FRONTEND_ARCHITECTURE.md`)

- `JobDescriptionListPage` — table with status badges, filter by department/status.
- `JobDescriptionFormPage` — create/edit, includes the scoring-criteria builder (dynamic rule-type form matching §3's schema).
- `JobDescriptionDetailPage` — description + criteria summary + link to candidates.
- `CandidateListPage` (scoped to a job) — upload dropzone, table with status badges, score, rank.
- `RankingPage` — ranked list view, score breakdown per candidate (bar per criterion, using the KPI-style score visual from `UI_DESIGN_SYSTEM.md` §4), shortlist/reject actions, export button.
- `CandidateDetailPage` — parsed data review/edit, per-criterion score breakdown, manual review scoring UI, override action; renders an "Unassigned — pick a job" state with an inline assign control when `jobDescriptionId` is null (see §11).
- `UnassignedCandidatesPage` — table of automatically-fetched candidates not yet matched to a job, with an inline "assign to job" action per row (see §11).

---

## 10. Edge Cases & Rules

- Duplicate CV upload (same email) for the same job → warn, don't silently create a duplicate candidate; let HR choose to replace or keep both.
- Re-scoring after criteria are edited: existing `CandidateScore` rows for that job's candidates should be recomputed, not left stale — editing criteria on a job with existing scored candidates should either (a) trigger a re-score of all candidates, or (b) clearly flag "criteria changed since last scoring" until re-run. Pick (a) by default for simplicity, confirm with HR via a dialog before doing it since it changes recorded scores.
- Closing a job description does not delete or hide existing candidate data — historical shortlisting reports must remain accurate after a job closes.

---

## 11. Automated CV Intake

Connects Job Descriptions and CV Screening end-to-end so HR doesn't manually upload every CV per role.

### Sources
- **Gmail** (`hr@kafi-group.com`) — CV attachments (PDF/DOCX) on inbound email. Each processed message gets a Gmail label (`HR-Agent-Processed`) applied so a re-sync never re-downloads it; the primary dedupe key is still `(source, source_ref)` on `Candidate`.
- **Google Form** — reads the form's linked response Sheet via the Sheets API, downloads the uploaded CV from Drive per row. New-row tracking uses a small local state file (`data/google_form_state.json`), so a re-sync only reads rows added since the last run.
- WhatsApp intake stays out of scope — not touched by this feature.

Both sources are wrapped so a missing/expired OAuth token, missing `GOOGLE_FORM_RESPONSES_SHEET_ID`, or any API error produces a clean per-source "not configured" / "fetch failed" result (`app/ingestion/cv_submission.py::SourceFetchResult`) — a sync never crashes because one source isn't set up yet.

### Trigger
Manual **"Sync CVs"** button in the CV Screening hub (`POST /cv-screening/sync`) — no background scheduler. Each run: fetches from both sources → dedupes → stores each new CV as an unassigned `Candidate` (`job_description_id = NULL`, `source`, `source_ref`, `submitted_at` set) → parses it → runs the AI job matcher against all currently **open** job descriptions.

### AI Matching (`app/scoring/cv_job_matcher.py`)
- Primary: Gemini reads the CV text (+ the applicant's stated position, e.g. email subject/form field) against every open job's title/description/requirements and returns `{job_description_id, confidence, reasoning}` as strict JSON.
- Fallback (no `GEMINI_API_KEY` configured): deterministic keyword overlap between the CV/position text and each job's title/requirements — capped confidence so it rarely crosses the auto-assign threshold without a strong signal, keeping the feature honestly "best-effort" without an AI key.
- `cv_auto_match_min_confidence` (`system_config`-style setting, default `0.55`) is the auto-assign threshold: at or above it, the candidate is assigned to that job and the normal parse/score/rank pipeline runs immediately; below it, the candidate stays unassigned with `match_confidence`/`match_reasoning` recorded as a "best guess" for HR to see.

### Unassigned Pool
- `GET /candidates/unassigned` lists candidates with no job yet — surfaced via the `UnassignedCandidatesPage` and a badge/link on the CV Screening hub whenever the count is above zero.
- `POST /candidates/{id}/assign` lets HR manually route (or re-route) a candidate to a job description; this re-runs the scoring pipeline against that job's criteria the same way an automated match does.
- `GET /candidates/{id}/evaluation` returns `business_rule_violation` (not a 500) for a candidate with no `job_description_id` — evaluation is meaningless before assignment.
- Nothing fetched is ever silently dropped — every CV lands either on a job or in the Unassigned pool.

### Audit Logging
- One summary entry per sync run (`candidate.cv_sync_run`, batch counts — not one row per candidate, mirroring the attendance-import logging pattern).
- `candidate.matched_to_job` (automated) and `candidate.assigned_to_job` (manual) are logged per candidate with confidence/reasoning in `after_state`.

### Operational Setup (one-time, outside code)
1. Create a Google Cloud OAuth client (Desktop app type); place the downloaded JSON at `backend/credentials/google_oauth_client.json` (gitignored).
2. Run a sync once locally to complete the interactive OAuth consent — this mints `credentials/gmail_token.json` / `credentials/form_token.json`.
3. Set `GOOGLE_FORM_RESPONSES_SHEET_ID` to the form's linked Sheet ID.
4. For cloud deploys with an ephemeral filesystem (Railway): paste the minted token file's contents into `GOOGLE_OAUTH_TOKEN_JSON`; on boot, `app/main.py` writes it back to `google_oauth_token_file` if that file doesn't already exist, so a redeploy doesn't require re-doing the interactive consent.
