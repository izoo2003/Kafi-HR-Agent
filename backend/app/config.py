"""Central configuration loader for the HR & Admin agent.

Loads environment variables (.env) plus the YAML rubric/role configs so every
module reads settings from one place.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"

load_dotenv(BASE_DIR / ".env")


def _yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    gmail_address: str
    google_oauth_credentials_file: Path
    google_oauth_token_file: Path
    google_form_sheet_id: str
    google_form_token_file: Path
    database_url: str
    reports_output_dir: Path

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            gmail_address=os.getenv("GMAIL_ADDRESS", "hr@kafi-group.com"),
            google_oauth_credentials_file=BASE_DIR
            / os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE", "credentials/google_oauth_client.json"),
            google_oauth_token_file=BASE_DIR
            / os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "credentials/gmail_token.json"),
            google_form_sheet_id=os.getenv("GOOGLE_FORM_RESPONSES_SHEET_ID", ""),
            google_form_token_file=BASE_DIR
            / os.getenv("GOOGLE_FORM_TOKEN_FILE", "credentials/form_token.json"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///data/hr_agent.db"),
            reports_output_dir=BASE_DIR / os.getenv("REPORTS_OUTPUT_DIR", "data/reports"),
        )


def load_scoring_rubric() -> dict[str, Any]:
    return _yaml(CONFIG_DIR / "scoring_rubric.yaml")


def load_role_profiles() -> dict[str, Any]:
    return _yaml(CONFIG_DIR / "roles.yaml")


settings = Settings.load()
