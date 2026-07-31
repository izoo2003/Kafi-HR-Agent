"""Application settings — env vars + paths into credentials/ and config/."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
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
    cors_origins: str = "http://localhost:5288,http://127.0.0.1:5288"
    # Optional regex for preview hosts (e.g. Vercel): https://.*\.vercel\.app
    cors_origin_regex: str = ""
    public_api_url: str = ""  # e.g. https://kafi-hr-agent.up.railway.app
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

    # --- Optional LLM / legacy ingestion (feature modules may use later) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    # --- Paths ---
    credentials_dir: Path = Field(default_factory=lambda: BASE_DIR / "credentials")
    config_dir: Path = Field(default_factory=lambda: BASE_DIR / "config")
    data_dir: Path = Field(default_factory=lambda: BASE_DIR / "data")
    uploads_cvs_dir: Path = Field(default_factory=lambda: BASE_DIR / "data" / "uploads" / "cvs")

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
