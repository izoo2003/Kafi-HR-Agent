"""Shared Google OAuth helper for Gmail + Sheets/Drive (Google Form
responses). Both ingestors reuse the same OAuth client (downloaded once from
Google Cloud Console) but keep separate token files/scopes.
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


class GoogleCredentialsNotConfigured(RuntimeError):
    """Raised when the OAuth client secrets file is missing — caller should
    treat this as "source not connected yet", not a crash."""


def get_credentials(
    client_secrets_file: Path,
    token_file: Path,
    scopes: list[str],
    *,
    interactive: bool = False,
) -> Credentials:
    """Returns valid OAuth credentials.

    By default (`interactive=False`) never opens a browser — Sync CVs must not
    block on Google consent. Pass `interactive=True` only for a deliberate
    local one-time auth CLI. Token is cached to `token_file`.
    """
    creds: Credentials | None = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets_file.exists():
                raise GoogleCredentialsNotConfigured(
                    f"Missing Google OAuth client secrets file at {client_secrets_file}. "
                    "Download it from Google Cloud Console (OAuth client ID, Desktop app) "
                    "and place it there, then authorize once with interactive=True."
                )
            if not interactive:
                raise GoogleCredentialsNotConfigured(
                    f"Google OAuth token missing at {token_file}. "
                    "Primary email intake is webmail IMAP (hr@kafi-group.com) — "
                    "Gmail API is optional. Authorize Gmail separately if needed; "
                    "Sync will not open a browser login."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), scopes)
            creds = flow.run_local_server(port=0)

        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return creds
