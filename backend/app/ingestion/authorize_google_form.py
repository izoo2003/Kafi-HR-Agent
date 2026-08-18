"""One-time local OAuth for Google Form CV sync (Sheets + Drive).

Run from the backend/ folder after placing the Desktop OAuth client JSON at
credentials/google_oauth_client.json:

    python -m app.ingestion.authorize_google_form

Sign in as the Google account that owns the form / responses spreadsheet.
Then paste the printed GOOGLE_FORM_TOKEN_JSON (and GOOGLE_OAUTH_CLIENT_JSON)
into Railway so Sync CVs works after deploys.
"""
from __future__ import annotations

import sys

from app.core.config import get_settings
from app.ingestion.google_auth import GoogleCredentialsNotConfigured, get_credentials
from app.ingestion.google_form_ingestor import SCOPES


def main() -> int:
    settings = get_settings()
    creds_path = settings.resolved_path(settings.google_oauth_credentials_file)
    token_path = settings.resolved_path(settings.google_form_token_file)

    if not creds_path.exists() and not (settings.google_oauth_client_json or "").strip():
        print(
            "Missing OAuth client secrets.\n\n"
            "1. Google Cloud Console → APIs & Services → Enable Google Sheets API and Google Drive API.\n"
            "2. Credentials → Create credentials → OAuth client ID → Desktop app.\n"
            "3. Download the JSON to:\n"
            f"   {creds_path}\n"
            "4. Re-run: python -m app.ingestion.authorize_google_form\n",
            file=sys.stderr,
        )
        return 1

    try:
        creds = get_credentials(
            creds_path,
            token_path,
            SCOPES,
            interactive=True,
            purpose="Google Form",
        )
    except GoogleCredentialsNotConfigured as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Authorized. Token saved to {token_path}")
    print()
    print("Set this Railway variable so Form sync survives deploys:")
    print("GOOGLE_FORM_TOKEN_JSON=")
    print(creds.to_json())
    if creds_path.exists():
        print()
        print("Also set GOOGLE_OAUTH_CLIENT_JSON to the full contents of:")
        print(str(creds_path))
    if not settings.google_form_sheet_id:
        print()
        print(
            "GOOGLE_FORM_RESPONSES_SHEET_ID is empty — copy the ID from the "
            "linked responses spreadsheet URL (.../spreadsheets/d/<ID>/edit)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
