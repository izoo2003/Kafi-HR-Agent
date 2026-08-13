"""Application settings — env vars + paths into credentials/ and config/."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = 8808
    api_reload: bool = False
    cors_origins: str = (
        "http://localhost:5288,http://127.0.0.1:5288,"
        "https://kafi-hr-agent.vercel.app"
    )
    # Allow Vercel production + preview hosts unless overridden.
    cors_origin_regex: str = r"https://.*\.vercel\.app"
    public_api_url: str = "https://kafi-hr-agent.up.railway.app"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production

    # --- Database ---
    database_url: str = "sqlite:///data/hr_agent.db"

    # --- Supabase (cloud project; SQLAlchemy still uses database_url) ---
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwks_url: str = ""
    supabase_project_ref: str = ""

    # --- JWT / Auth ---
    jwt_secret_key: str = "CHANGE_ME_dev_only_hr_admin_agent"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Seed admin (first boot only) ---
    seed_admin_email: str = "admin@kafi-group.com"
    seed_admin_password: str = "ChangeMeAdmin123!"
    seed_admin_name: str = "System Admin"

    # --- Optional LLM ---
    # CV screening / matching / evaluation
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    # Job posting AI Analyzer only (description + requirements draft) — separate key
    gemini_job_posting_api_key: str = ""
    gemini_job_posting_model: str = "gemini-flash-latest"

    # --- Automated CV intake (FEATURE_CV_SCREENING.md §11) ---
    # All blank-safe: sync reports a source as "not configured" rather than failing.
    gmail_address: str = "hr@kafi-group.com"
    google_oauth_credentials_file: str = "credentials/google_oauth_client.json"
    google_oauth_token_file: str = "credentials/gmail_token.json"
    google_form_sheet_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GOOGLE_FORM_RESPONSES_SHEET_ID",
            "google_form_sheet_id",
            "GOOGLE_FORM_SHEET_ID",
        ),
    )
    google_form_token_file: str = "credentials/form_token.json"
    # If set, written to google_oauth_token_file on boot when that file is missing —
    # lets a token minted once locally survive an ephemeral-filesystem redeploy (Railway).
    google_oauth_token_json: str = ""
    # HR webmail via IMAP (mail.kafi-group.com) — primary for hr@kafi-group.com
    imap_host: str = "mail.kafi-group.com"
    imap_port: int = 993
    imap_user: str = "hr@kafi-group.com"
    imap_password: str = ""
    imap_ssl: bool = True

    @field_validator("imap_password", mode="before")
    @classmethod
    def strip_imap_password_quotes(cls, value: object) -> object:
        """Railway/.env pastes sometimes keep surrounding quotes; strip them."""
        if not isinstance(value, str):
            return value
        v = value.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            return v[1:-1]
        return v

    # Microsoft Graph / Outlook 365 — optional if Graph app is configured
    outlook_mailbox: str = Field(
        default="hr@kafi-group.com",
        validation_alias=AliasChoices("OUTLOOK_MAILBOX", "outlook_mailbox"),
    )
    ms_graph_tenant_id: str = ""
    ms_graph_client_id: str = ""
    ms_graph_client_secret: str = ""
    # Meta WhatsApp Cloud API (document CVs → pending queue → Sync)
    whatsapp_display_number: str = "+923330313511"
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_api_version: str = "v21.0"
    cv_auto_match_min_confidence: float = 0.55

    # --- Paths ---
    credentials_dir: Path = Field(default_factory=lambda: BASE_DIR / "credentials")
    config_dir: Path = Field(default_factory=lambda: BASE_DIR / "config")
    data_dir: Path = Field(default_factory=lambda: BASE_DIR / "data")
    uploads_cvs_dir: Path = Field(default_factory=lambda: BASE_DIR / "data" / "uploads" / "cvs")
    cv_files_dir: Path = Field(default_factory=lambda: BASE_DIR / "data" / "cv_files")

    def resolved_path(self, relative_or_absolute: str) -> Path:
        """Resolves a credentials-style setting (path relative to backend/) to an absolute Path."""
        p = Path(relative_or_absolute)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def sqlite_path(self) -> Path | None:
        if self.database_url.startswith("sqlite:///"):
            rel = self.database_url.removeprefix("sqlite:///")
            path = Path(rel)
            return path if path.is_absolute() else BASE_DIR / path
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
