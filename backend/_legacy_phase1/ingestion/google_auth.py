"""Shared Google OAuth helper for Gmail + Sheets/Drive (Google Form
responses). Both ingestors reuse the same OAuth client (downloaded once from
Google Cloud Console) but keep separate token files/scopes.
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def get_credentials(
    client_secrets_file: Path, token_file: Path, scopes: list[str]
) -> Credentials:
    """Returns valid OAuth credentials, running the interactive consent flow
    the first time and refreshing silently afterwards. Token is cached to
    `token_file` so this only needs a browser login once per scope set.
    """
    creds: Credentials | None = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets_file.exists():
                raise FileNotFoundError(
                    f"Missing Google OAuth client secrets file at {client_secrets_file}. "
                    "Download it from Google Cloud Console (OAuth client ID, Desktop app) "
                    "and place it there. See credentials/README.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), scopes)
            creds = flow.run_local_server(port=0)

        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return creds
