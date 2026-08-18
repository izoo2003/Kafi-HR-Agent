"""Shared Google OAuth / service-account helper for Sheets/Drive (Google Form
responses) and optional Gmail. FEATURE_CV_SCREENING.md §11.

Railway has an ephemeral filesystem, so client secrets and minted tokens are
restored from env vars on boot (GOOGLE_OAUTH_CLIENT_JSON, GOOGLE_FORM_TOKEN_JSON,
GOOGLE_SERVICE_ACCOUNT_JSON).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


class GoogleCredentialsNotConfigured(RuntimeError):
    """Raised when OAuth client secrets / token are missing — caller should
    treat this as "source not connected yet", not a crash."""


def restore_google_credential_files(settings) -> None:
    """Write env-provided JSON onto disk when the file is missing (Railway)."""
    pairs = (
        (settings.google_oauth_client_json, settings.google_oauth_credentials_file),
        (settings.google_oauth_token_json, settings.google_oauth_token_file),
        (settings.google_form_token_json, settings.google_form_token_file),
        (settings.google_service_account_json, "credentials/google_service_account.json"),
    )
    for contents, relative in pairs:
        raw = (contents or "").strip()
        if not raw:
            continue
        path = settings.resolved_path(relative)
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
        logger.info("Restored %s from environment", path.name)
        print(f"[startup] Restored {path.name} from env", flush=True)


def get_credentials(
    client_secrets_file: Path,
    token_file: Path,
    scopes: list[str],
    *,
    interactive: bool = False,
    purpose: str = "Google",
) -> Credentials:
    """Returns valid OAuth or service-account credentials.

    By default (`interactive=False`) never opens a browser — Sync CVs must not
    block on Google consent. Pass `interactive=True` only for a deliberate
    local one-time auth CLI. Token is cached to `token_file`.
    """
    from app.core.config import get_settings

    settings = get_settings()
    restore_google_credential_files(settings)

    sa_creds = _service_account_credentials(settings, scopes)
    if sa_creds is not None:
        return sa_creds

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
                    "Create an OAuth client (Desktop app) in Google Cloud Console, enable "
                    "Google Sheets API + Google Drive API, download the JSON, and either "
                    "place it there or set GOOGLE_OAUTH_CLIENT_JSON. Then run: "
                    "python -m app.ingestion.authorize_google_form"
                )
            if not interactive:
                raise GoogleCredentialsNotConfigured(
                    f"{purpose} OAuth token missing at {token_file}. "
                    "Authorize once on a machine with a browser: "
                    "python -m app.ingestion.authorize_google_form "
                    "then set GOOGLE_FORM_TOKEN_JSON on Railway to the printed token JSON."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), scopes)
            try:
                creds = flow.run_local_server(
                    host="127.0.0.1",
                    port=8765,
                    authorization_prompt_message=(
                        "Open the browser sign-in, then return here after Google redirects "
                        "to http://127.0.0.1:8765/ ..."
                    ),
                    success_message=(
                        f"{purpose} authorization complete. You can close this browser tab."
                    ),
                    open_browser=True,
                )
            except OSError:
                # Fall back if a local process is already using the preferred port.
                creds = flow.run_local_server(
                    host="127.0.0.1",
                    port=0,
                    authorization_prompt_message=(
                        "Open the browser sign-in, then return here after Google redirects "
                        "to the temporary 127.0.0.1 callback URL ..."
                    ),
                    success_message=(
                        f"{purpose} authorization complete. You can close this browser tab."
                    ),
                    open_browser=True,
                )

        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _service_account_credentials(settings, scopes: list[str]):
    raw = (settings.google_service_account_json or "").strip()
    sa_path = settings.resolved_path("credentials/google_service_account.json")
    if not raw and not sa_path.exists():
        return None
    from google.oauth2 import service_account

    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)
    return service_account.Credentials.from_service_account_file(str(sa_path), scopes=scopes)
