# Google Form — CV Submission Form (field spec)

Create this as a new Google Form, then link it to a Google Sheet for
responses (Form → Responses tab → green Sheets icon → "Create spreadsheet").
Copy the resulting Sheet ID into `.env` as `GOOGLE_FORM_RESPONSES_SHEET_ID`.

The ingestion code (`app/ingestion/google_form_ingestor.py`) matches header
text case-insensitively, so use these exact field titles (or the aliases
already coded in) to avoid any mismatch.

## Fields

| # | Field title | Type | Required | Notes |
|---|---|---|---|---|
| 1 | Full Name | Short answer | Yes | |
| 2 | Email Address | Short answer (with email validation) | Yes | Used to dedupe candidates |
| 3 | Phone Number | Short answer | Yes | |
| 4 | Position Applied For | Dropdown or Short answer | Yes | Ideally a dropdown listing current open roles (keep in sync with `config/roles.yaml` titles) so matching is exact |
| 5 | Upload your CV/Resume | File upload | Yes | Restrict to PDF/DOCX, max 1 file, max ~10MB |
| 6 | Current Location / City | Short answer | No | |
| 7 | LinkedIn / Portfolio (optional) | Short answer | No | Not ingested yet, but fine to collect for later |

## Settings to enable

- **Responses → Collect email addresses**: Off (we already ask for it explicitly above, keeps behavior consistent regardless of Google account).
- **File upload question → "Only allow specific file types"**: PDF, DOCX.
- **File upload question → Maximum number of files**: 1.
- **General → Restrict to users in organization**: Off (external applicants must be able to submit).
- Link responses to a **Google Sheet** (not just Google Forms' built-in view) — the ingestor reads the Sheet, not the Form directly.

## Why this shape

This mirrors exactly what the Gmail path already produces (name, email,
phone, position, CV file, optional location) so both sources normalize into
the same `CandidateSubmission` record before scoring — the rest of the
pipeline (parsing → scoring → ranking → reporting) doesn't need to know
which channel a CV came from.
