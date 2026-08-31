"""Application settings — env vars + paths into credentials/ and config/."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


from app.core.gemini_client import parse_model_chain


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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
    # Private Storage bucket for employee + referral document binaries
    supabase_storage_bucket: str = "employee-documents"

    # --- JWT / Auth ---
    jwt_secret_key: str = "CHANGE_ME_dev_only_hr_admin_agent"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Seed admin (first boot only) ---
    seed_admin_email: str = "admin@kafi-group.com"
    seed_admin_password: str = "Admin123"
    seed_admin_name: str = "System Admin"

    # --- Optional LLM ---
    # CV parse/score/evaluation + optional mail CV-vs-not-CV classifier
    # Primary + rotation key: when one is quota-exhausted, switch to the other.
    gemini_api_key: str = ""
    gemini_api_key_2: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # Sync CVs: route a fetched CV to the best matching job (any status)
    gemini_cv_match_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GEMINI_CV_MATCH_API_KEY",
            "gemini_cv_match_api_key",
            "GEMINI_CV_MATCH_KEY",
        ),
    )
    gemini_cv_match_api_key_2: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GEMINI_CV_MATCH_API_KEY_2",
            "gemini_cv_match_api_key_2",
        ),
    )
    gemini_cv_match_model: str = "gemini-3.5-flash-lite"
    gemini_cv_match_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # CNIC image verification (falls back to gemini_api_key pool)
    gemini_cnic_api_key: str = ""
    gemini_cnic_api_key_2: str = ""
    gemini_cnic_model: str = "gemini-3.5-flash-lite"
    gemini_cnic_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # Education marks/grade sheet verification — separate key (falls back to gemini_api_key pool)
    gemini_education_api_key: str = ""
    gemini_education_api_key_2: str = ""
    gemini_education_model: str = "gemini-3.5-flash-lite"
    gemini_education_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # Appointment / contract letter image verification (falls back to gemini_api_key pool)
    gemini_letter_api_key: str = ""
    gemini_letter_api_key_2: str = ""
    gemini_letter_model: str = "gemini-3.5-flash-lite"
    gemini_letter_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # Job posting AI Analyzer only (description + requirements draft) — separate key
    gemini_job_posting_api_key: str = ""
    gemini_job_posting_api_key_2: str = ""
    gemini_job_posting_model: str = "gemini-3.5-flash-lite"
    gemini_job_posting_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # Department JD / SOP drafts — dedicated keys, each with its own model chain
    gemini_department_api_key: str = ""
    gemini_department_api_key_2: str = ""
    gemini_department_model: str = "gemini-3.5-flash-lite"
    gemini_department_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    gemini_department_model_2: str = "gemini-3.6-flash"
    gemini_department_model_fallbacks_2: str = (
        "gemini-3.5-flash-lite,gemini-3.5-flash,gemini-3.1-flash-lite"
    )
    # Payroll salary-sheet AI summary (payment modes + narrative) — separate key
    gemini_payroll_api_key: str = ""
    gemini_payroll_api_key_2: str = ""
    gemini_payroll_model: str = "gemini-3.5-flash-lite"
    gemini_payroll_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # Employee performance monthly AI summary — separate key
    gemini_performance_api_key: str = ""
    gemini_performance_api_key_2: str = ""
    gemini_performance_model: str = "gemini-3.5-flash-lite"
    gemini_performance_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    # Employee training course recommendations — separate key
    gemini_training_api_key: str = ""
    gemini_training_api_key_2: str = ""
    gemini_training_model: str = "gemini-3.5-flash-lite"
    gemini_training_model_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"

    # Cloudflare Workers AI — job posting recruitment image generation
    cloudflare_account_id: str = Field(
        default="",
        validation_alias=AliasChoices("CLOUDFLARE_ACCOUNT_ID", "cloudflare_account_id"),
    )
    cloudflare_api_token: str = Field(
        default="",
        validation_alias=AliasChoices("CLOUDFLARE_API_TOKEN", "cloudflare_api_token"),
    )
    cloudflare_image_model: str = Field(
        default="@cf/black-forest-labs/flux-1-schnell",
        validation_alias=AliasChoices("CLOUDFLARE_IMAGE_MODEL", "cloudflare_image_model"),
    )
    cloudflare_image_steps: int = Field(
        default=4,
        validation_alias=AliasChoices("CLOUDFLARE_IMAGE_STEPS", "cloudflare_image_steps"),
    )
    cloudflare_image_timeout: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "CLOUDFLARE_IMAGE_TIMEOUT", "cloudflare_image_timeout"
        ),
    )
    # Shown on generated hiring posters
    hiring_apply_email: str = Field(
        default="hr@kafi-group.com",
        validation_alias=AliasChoices("HIRING_APPLY_EMAIL", "hiring_apply_email"),
    )
    company_display_name: str = Field(
        default="Kafi Group",
        validation_alias=AliasChoices("COMPANY_DISPLAY_NAME", "company_display_name"),
    )

    # LinkedIn feed post when a job description is set to Open (reuse the same
    # developer app client id/secret + member tokens from a previous agent).
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_access_token: str = ""
    linkedin_refresh_token: str = ""
    linkedin_author_urn: str = ""  # urn:li:person:… or urn:li:organization:…
    linkedin_account_1_label: str = ""
    linkedin_account_2_access_token: str = ""
    linkedin_account_2_label: str = ""
    linkedin_account_3_access_token: str = ""
    linkedin_account_3_label: str = ""
    linkedin_organization_id: str = ""
    linkedin_accounts_json: str = ""  # optional JSON list override
    linkedin_api_version: str = ""  # blank = current YYYYMM (e.g. 202608)

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
    # Public apply URL pasted into job posting descriptions (candidates submit details + CV here).
    google_form_url: str = Field(
        default=(
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLSeUDm87ou1gbO90VPMyrRJYORgHatluwM6xmmUdJgqSZobWmQ/viewform?usp=sharing"
        ),
        validation_alias=AliasChoices("GOOGLE_FORM_URL", "google_form_url"),
    )
    google_form_token_file: str = "credentials/form_token.json"
    # If set, written to google_oauth_token_file on boot when that file is missing —
    # lets a token minted once locally survive an ephemeral-filesystem redeploy (Railway).
    google_oauth_token_json: str = ""
    google_oauth_client_json: str = ""
    google_form_token_json: str = ""
    google_service_account_json: str = ""
    # Comma-separated CV sync sources. Default is the two live intake channels.
    cv_sync_sources: str = "webmail,google_form"
    cv_sync_batch_size: int = Field(default=20, ge=1, le=100)
    cv_sync_time_budget_seconds: float = Field(default=120.0, ge=15.0, le=600.0)
    # HR webmail via IMAP (mail.kafi-group.com) — primary for hr@kafi-group.com
    imap_host: str = "mail.kafi-group.com"
    imap_port: int = 993
    imap_user: str = "hr@kafi-group.com"
    imap_password: str = ""
    imap_ssl: bool = True
    # TCP target when imap_host is Cloudflare-proxied (IMAP cannot use orange-cloud DNS).
    # Default is the cPanel origin MX for kafi-group.com — required on Railway where UDP
    # DNS to 8.8.8.8 may fail and mail.kafi-group.com only resolves to Cloudflare.
    imap_connect_host: str = "_dc-mx.32098f035483.kafi-group.com"
    imap_tls_server_name: str = "mail.kafi-group.com"

    @field_validator(
        "imap_password",
        "linkedin_access_token",
        "linkedin_refresh_token",
        "linkedin_client_secret",
        "linkedin_account_2_access_token",
        "linkedin_account_3_access_token",
        mode="before",
    )
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
    uploads_employees_dir: Path = Field(
        default_factory=lambda: BASE_DIR / "data" / "uploads" / "employees"
    )
    cv_files_dir: Path = Field(default_factory=lambda: BASE_DIR / "data" / "cv_files")

    def resolved_path(self, relative_or_absolute: str) -> Path:
        """Resolves a credentials-style setting (path relative to backend/) to an absolute Path."""
        p = Path(relative_or_absolute)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @staticmethod
    def _valid_keys(*candidates: str) -> list[str]:
        out: list[str] = []
        for raw in candidates:
            key = (raw or "").strip()
            if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
                key = key[1:-1].strip()
            if not key or key.startswith("your_"):
                continue
            if key not in out:
                out.append(key)
        return out

    def resolved_gemini_api_key(self) -> str:
        keys = self.resolved_gemini_api_keys()
        return keys[0] if keys else ""

    def resolved_gemini_api_keys(self) -> list[str]:
        return self._valid_keys(self.gemini_api_key, self.gemini_api_key_2)

    def resolved_gemini_cv_match_api_key(self) -> str:
        keys = self.resolved_gemini_cv_match_api_keys()
        return keys[0] if keys else ""

    def resolved_gemini_cv_match_api_keys(self) -> list[str]:
        import os

        dedicated = self._valid_keys(
            self.gemini_cv_match_api_key,
            self.gemini_cv_match_api_key_2,
            os.environ.get("GEMINI_CV_MATCH_API_KEY", ""),
            os.environ.get("GEMINI_CV_MATCH_API_KEY_2", ""),
        )
        if dedicated:
            return dedicated
        return self.resolved_gemini_api_keys()

    def resolved_gemini_cv_match_model(self) -> str:
        return (self.gemini_cv_match_model or self.gemini_model or "gemini-3.5-flash-lite").strip()

    def resolved_gemini_models(self) -> list[str]:
        primary = (self.gemini_model or "gemini-3.5-flash-lite").strip()
        return parse_model_chain(primary, self.gemini_model_fallbacks)

    def resolved_gemini_cv_match_models(self) -> list[str]:
        primary = self.resolved_gemini_cv_match_model()
        fallbacks = self.gemini_cv_match_model_fallbacks or self.gemini_model_fallbacks
        return parse_model_chain(primary, fallbacks)

    def resolved_gemini_cnic_api_key(self) -> str:
        keys = self.resolved_gemini_cnic_api_keys()
        return keys[0] if keys else ""

    def resolved_gemini_cnic_api_keys(self) -> list[str]:
        dedicated = self._valid_keys(self.gemini_cnic_api_key, self.gemini_cnic_api_key_2)
        if dedicated:
            return dedicated
        return self.resolved_gemini_api_keys()

    def resolved_gemini_cnic_models(self) -> list[str]:
        primary = (
            self.gemini_cnic_model or self.gemini_model or "gemini-3.5-flash-lite"
        ).strip()
        fallbacks = self.gemini_cnic_model_fallbacks or self.gemini_model_fallbacks
        return parse_model_chain(primary, fallbacks)

    def resolved_gemini_education_api_key(self) -> str:
        keys = self.resolved_gemini_education_api_keys()
        return keys[0] if keys else ""

    def resolved_gemini_education_api_keys(self) -> list[str]:
        dedicated = self._valid_keys(
            self.gemini_education_api_key, self.gemini_education_api_key_2
        )
        if dedicated:
            return dedicated
        return self.resolved_gemini_api_keys()

    def resolved_gemini_education_models(self) -> list[str]:
        primary = (
            self.gemini_education_model or self.gemini_model or "gemini-3.5-flash-lite"
        ).strip()
        fallbacks = (
            self.gemini_education_model_fallbacks or self.gemini_model_fallbacks
        )
        return parse_model_chain(primary, fallbacks)

    def resolved_gemini_letter_api_keys(self) -> list[str]:
        dedicated = self._valid_keys(
            self.gemini_letter_api_key, self.gemini_letter_api_key_2
        )
        if dedicated:
            return dedicated
        return self.resolved_gemini_api_keys()

    def resolved_gemini_letter_models(self) -> list[str]:
        primary = (
            self.gemini_letter_model or self.gemini_model or "gemini-3.5-flash-lite"
        ).strip()
        fallbacks = self.gemini_letter_model_fallbacks or self.gemini_model_fallbacks
        return parse_model_chain(primary, fallbacks)

    def resolved_gemini_job_posting_api_key(self) -> str:
        keys = self.resolved_gemini_job_posting_api_keys()
        return keys[0] if keys else ""

    def resolved_gemini_job_posting_api_keys(self) -> list[str]:
        return self._valid_keys(
            self.gemini_job_posting_api_key, self.gemini_job_posting_api_key_2
        )

    def resolved_gemini_job_posting_models(self) -> list[str]:
        primary = (
            self.gemini_job_posting_model or self.gemini_model or "gemini-3.5-flash-lite"
        ).strip()
        fallbacks = (
            self.gemini_job_posting_model_fallbacks or self.gemini_model_fallbacks
        )
        return parse_model_chain(primary, fallbacks)

    def resolved_gemini_department_api_keys(self) -> list[str]:
        dedicated = self._valid_keys(
            self.gemini_department_api_key, self.gemini_department_api_key_2
        )
        if dedicated:
            return dedicated
        job_keys = self.resolved_gemini_job_posting_api_keys()
        if job_keys:
            return job_keys
        return self.resolved_gemini_api_keys()

    def resolved_gemini_department_key_chains(self) -> list[tuple[str, list[str]]]:
        """Per-key (base + fallbacks) for department JD/SOP generation."""
        key_1 = (self.gemini_department_api_key or "").strip()
        key_2 = (self.gemini_department_api_key_2 or "").strip()
        chain_1 = parse_model_chain(
            (self.gemini_department_model or self.gemini_model or "gemini-3.5-flash-lite").strip(),
            self.gemini_department_model_fallbacks or self.gemini_model_fallbacks,
        )
        chain_2 = parse_model_chain(
            (
                self.gemini_department_model_2
                or self.gemini_department_model
                or self.gemini_model
                or "gemini-3.6-flash"
            ).strip(),
            self.gemini_department_model_fallbacks_2
            or self.gemini_department_model_fallbacks
            or self.gemini_model_fallbacks,
        )
        chains: list[tuple[str, list[str]]] = []
        if key_1 and not key_1.startswith("your_"):
            chains.append((key_1, chain_1))
        if key_2 and not key_2.startswith("your_") and key_2 != key_1:
            chains.append((key_2, chain_2))
        if chains:
            return chains
        keys = self.resolved_gemini_department_api_keys()
        models = (
            self.resolved_gemini_job_posting_models()
            if self.resolved_gemini_job_posting_api_keys()
            else self.resolved_gemini_models()
        )
        return [(key, models) for key in keys]

    def resolved_gemini_payroll_api_keys(self) -> list[str]:
        dedicated = self._valid_keys(
            self.gemini_payroll_api_key, self.gemini_payroll_api_key_2
        )
        if dedicated:
            return dedicated
        return self.resolved_gemini_api_keys()

    def resolved_gemini_payroll_models(self) -> list[str]:
        primary = (
            self.gemini_payroll_model or self.gemini_model or "gemini-3.5-flash-lite"
        ).strip()
        fallbacks = self.gemini_payroll_model_fallbacks or self.gemini_model_fallbacks
        return parse_model_chain(primary, fallbacks)

    def resolved_gemini_performance_api_keys(self) -> list[str]:
        dedicated = self._valid_keys(
            self.gemini_performance_api_key, self.gemini_performance_api_key_2
        )
        if dedicated:
            return dedicated
        return self.resolved_gemini_api_keys()

    def resolved_gemini_performance_models(self) -> list[str]:
        primary = (
            self.gemini_performance_model or self.gemini_model or "gemini-3.5-flash-lite"
        ).strip()
        fallbacks = (
            self.gemini_performance_model_fallbacks or self.gemini_model_fallbacks
        )
        return parse_model_chain(primary, fallbacks)

    def resolved_gemini_training_api_keys(self) -> list[str]:
        dedicated = self._valid_keys(
            self.gemini_training_api_key, self.gemini_training_api_key_2
        )
        if dedicated:
            return dedicated
        return self.resolved_gemini_api_keys()

    def resolved_gemini_training_models(self) -> list[str]:
        primary = (
            self.gemini_training_model or self.gemini_model or "gemini-3.5-flash-lite"
        ).strip()
        fallbacks = self.gemini_training_model_fallbacks or self.gemini_model_fallbacks
        return parse_model_chain(primary, fallbacks)

    def sqlite_path(self) -> Path | None:
        if self.database_url.startswith("sqlite:///"):
            rel = self.database_url.removeprefix("sqlite:///")
            path = Path(rel)
            return path if path.is_absolute() else BASE_DIR / path
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
