"""Post a job opening to LinkedIn feed(s) when a Job Description is set Open.

This is a Share/Posts API integration (organic feed post with the Google Form
apply link) — not LinkedIn Talent Solutions Job Posting API, which requires a
separate partner contract.

Tokens from the same LinkedIn developer app used by a previous agent work here:
client id/secret are app-level; access/refresh tokens are account-level.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.cv_screening import JobDescription
from app.models.system import SystemConfig

logger = logging.getLogger(__name__)

ACCOUNTS_CONFIG_KEY = "linkedin.accounts"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
POSTS_URL = "https://api.linkedin.com/rest/posts"
ME_URL = "https://api.linkedin.com/v2/userinfo"
COMMENTARY_MAX = 2900
# LinkedIn Marketing APIs support each YYYYMM version for ~12 months.
# Rolling fallbacks are generated from UTC now — do not hardcode 2025 months.


def ensure_linkedin_schema(db: Session) -> None:
    """create_all will not add columns on existing tables."""
    bind = db.get_bind()
    if bind is None:
        return
    dialect = bind.dialect.name
    if dialect == "sqlite":
        cols = {
            row[1] for row in db.execute(text("PRAGMA table_info(job_descriptions)")).fetchall()
        }
        if cols and "linkedin_posts" not in cols:
            db.execute(text("ALTER TABLE job_descriptions ADD COLUMN linkedin_posts JSON"))
        return
    if dialect == "postgresql":
        db.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS linkedin_posts JSON"))


def publish_job_if_open(
    db: Session,
    job: JobDescription,
    selected_names: list[str] | None = None,
) -> None:
    """Best-effort: never raises into the job-save path.

    Posts only to `selected_names` (from the Open-job LinkedIn picker). None or
    empty means skip posting — never blast every account unless HR chose them.
    """
    if (job.status or "").strip().lower() != "open":
        return
    if not selected_names:
        return
    try:
        ensure_linkedin_schema(db)
        results = _publish(db, job, selected_names=[n.strip() for n in selected_names if n.strip()])
        if results:
            job.linkedin_posts = results
            db.flush()
    except Exception:  # noqa: BLE001
        logger.exception("LinkedIn publish failed for job %s", job.id)


_HOW_TO_APPLY_RE = re.compile(r"\n\nHow to apply\s*[\s\S]*$", re.IGNORECASE)


def _normalize_apply_url(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        return raw
    return "https://" + raw.lstrip("/")


def list_public_accounts() -> list[dict[str, str]]:
    """Labels only — never tokens — for the Open-job picker."""
    accounts = _env_accounts(get_settings())
    return [
        {
            "name": str(a.get("name") or ""),
            "label": str(a.get("label") or a.get("name") or "LinkedIn account"),
        }
        for a in accounts
        if a.get("name")
    ]


def _publish(
    db: Session, job: JobDescription, selected_names: list[str]
) -> list[dict[str, Any]] | None:
    settings = get_settings()
    try:
        accounts = _load_accounts(db, settings)
    except json.JSONDecodeError as exc:
        return [
            {
                "account": "config",
                "label": "Config",
                "author_urn": None,
                "post_urn": None,
                "posted_at": None,
                "error": f"LINKEDIN_ACCOUNTS_JSON is not valid JSON: {exc}",
            }
        ]
    wanted = {n.lower() for n in selected_names}
    accounts = [
        a
        for a in accounts
        if str(a.get("name") or "").lower() in wanted
        or str(a.get("label") or "").lower() in wanted
    ]
    if not accounts:
        return list(job.linkedin_posts or []) or None

    existing = list(job.linkedin_posts or [])
    by_name = {str(row.get("account") or "default"): row for row in existing}
    apply_url = _normalize_apply_url(settings.google_form_url)
    commentary = _build_commentary(job, apply_url)
    changed = False

    for account in accounts:
        name = str(account.get("name") or "default")
        prior = by_name.get(name) or {}
        if prior.get("post_urn"):
            if not prior.get("post_url"):
                by_name[name] = {
                    **prior,
                    "post_url": linkedin_post_view_url(str(prior.get("post_urn") or "")),
                }
                changed = True
            continue
        changed = True
        try:
            token, account = _ensure_access_token(db, settings, account)
            author = _resolve_author_urn(token, account, settings)
            try:
                post_urn = _create_post(
                    token=token,
                    author_urn=author,
                    commentary=commentary,
                    apply_url=apply_url,
                    title=job.title,
                    description=(job.description_text or "")[:240],
                    version=settings.linkedin_api_version,
                )
            except RuntimeError as exc:
                if "401" not in str(exc) or not (account.get("refresh_token") or "").strip():
                    raise
                refreshed = _refresh_access_token(settings, account)
                account = {**account, **refreshed}
                _save_account_tokens(db, account)
                token = account["access_token"]
                author = _resolve_author_urn(token, account, settings)
                post_urn = _create_post(
                    token=token,
                    author_urn=author,
                    commentary=commentary,
                    apply_url=apply_url,
                    title=job.title,
                    description=(job.description_text or "")[:240],
                    version=settings.linkedin_api_version,
                )
            by_name[name] = {
                "account": name,
                "label": account.get("label") or name,
                "author_urn": author,
                "post_urn": post_urn,
                "post_url": linkedin_post_view_url(post_urn),
                "posted_at": datetime.now(UTC).isoformat(),
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("LinkedIn post failed for account %s: %s", name, exc)
            by_name[name] = {
                "account": name,
                "label": account.get("label") or name,
                "author_urn": account.get("author_urn"),
                "post_urn": None,
                "post_url": None,
                "posted_at": None,
                "error": str(exc)[:500],
            }

    if not changed:
        return existing
    return list(by_name.values())


def _numbered_env_accounts(settings: Settings) -> list[dict[str, Any]]:
    """LINKEDIN_ACCESS_TOKEN + LINKEDIN_ACCOUNT_2/3_* from the previous agent."""
    rows: list[tuple[str, str, str]] = [
        (
            "account_1",
            (settings.linkedin_account_1_label or "Account 1").strip() or "Account 1",
            (settings.linkedin_access_token or "").strip(),
        ),
        (
            "account_2",
            (settings.linkedin_account_2_label or "Account 2").strip() or "Account 2",
            (settings.linkedin_account_2_access_token or "").strip(),
        ),
        (
            "account_3",
            (settings.linkedin_account_3_label or "Account 3").strip() or "Account 3",
            (settings.linkedin_account_3_access_token or "").strip(),
        ),
    ]
    accounts: list[dict[str, Any]] = []
    for name, label, token in rows:
        if not token:
            continue
        accounts.append(
            {
                "name": name,
                "label": label,
                "access_token": token,
                "refresh_token": (settings.linkedin_refresh_token or "").strip()
                if name == "account_1"
                else "",
                "author_urn": "",
            }
        )
    return accounts


def _env_accounts(settings: Settings) -> list[dict[str, Any]]:
    numbered = _numbered_env_accounts(settings)
    if numbered:
        return numbered
    raw = (settings.linkedin_accounts_json or "").strip()
    accounts: list[dict[str, Any]] = []
    if raw:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("LINKEDIN_ACCOUNTS_JSON must be a JSON array")
        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            accounts.append(
                {
                    "name": str(item.get("name") or f"account_{idx + 1}"),
                    "label": str(item.get("label") or item.get("name") or f"Account {idx + 1}"),
                    "access_token": (item.get("access_token") or "").strip(),
                    "refresh_token": (item.get("refresh_token") or "").strip(),
                    "author_urn": (item.get("author_urn") or item.get("organization_urn") or "").strip(),
                }
            )
    return [a for a in accounts if a.get("access_token") or a.get("refresh_token")]


def _load_accounts(db: Session, settings: Settings) -> list[dict[str, Any]]:
    env_accounts = _env_accounts(settings)
    row = db.query(SystemConfig).filter(SystemConfig.key == ACCOUNTS_CONFIG_KEY).one_or_none()
    stored = row.value if row and isinstance(row.value, list) else []
    if not stored:
        return env_accounts
    stored_by_name = {str(a.get("name") or "default"): a for a in stored if isinstance(a, dict)}
    if not env_accounts:
        return [a for a in stored if isinstance(a, dict)]
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for env in env_accounts:
        name = str(env.get("name") or "default")
        seen.add(name)
        prev = stored_by_name.get(name) or {}
        merged.append(
            {
                **env,
                "access_token": (env.get("access_token") or prev.get("access_token") or "").strip(),
                "refresh_token": (env.get("refresh_token") or prev.get("refresh_token") or "").strip(),
                "author_urn": (env.get("author_urn") or prev.get("author_urn") or "").strip(),
                "label": env.get("label") or prev.get("label") or name,
            }
        )
    return merged


def _save_account_tokens(db: Session, account: dict[str, Any]) -> None:
    settings = get_settings()
    accounts = _load_accounts(db, settings)
    name = str(account.get("name") or "default")
    updated = False
    for idx, row in enumerate(accounts):
        if str(row.get("name") or "default") == name:
            accounts[idx] = {**row, **account}
            updated = True
            break
    if not updated:
        accounts.append(account)
    existing = db.query(SystemConfig).filter(SystemConfig.key == ACCOUNTS_CONFIG_KEY).one_or_none()
    if existing is None:
        db.add(SystemConfig(key=ACCOUNTS_CONFIG_KEY, value=accounts, updated_by=None))
    else:
        existing.value = accounts
    db.flush()


def _ensure_access_token(
    db: Session, settings: Settings, account: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    token = (account.get("access_token") or "").strip()
    if token:
        return token, account
    refreshed = _refresh_access_token(settings, account)
    account = {**account, **refreshed}
    _save_account_tokens(db, account)
    return account["access_token"], account


def _refresh_access_token(settings: Settings, account: dict[str, Any]) -> dict[str, str]:
    refresh = (account.get("refresh_token") or "").strip()
    client_id = (settings.linkedin_client_id or "").strip()
    client_secret = (settings.linkedin_client_secret or "").strip()
    if not refresh:
        raise RuntimeError("LinkedIn access token missing and no refresh_token is configured")
    if not client_id or not client_secret:
        raise RuntimeError(
            "LinkedIn token expired — set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET to refresh it"
        )
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(_linkedin_error(response, "token refresh"))
    data = response.json()
    access = (data.get("access_token") or "").strip()
    if not access:
        raise RuntimeError("LinkedIn refresh did not return an access_token")
    out = {"access_token": access}
    if data.get("refresh_token"):
        out["refresh_token"] = str(data["refresh_token"])
    return out


def _auth_headers(token: str, version: str) -> dict[str, str]:
    # Official header name is Linkedin-Version (YYYYMM). LinkedIn-Version is
    # accepted as an alias by most gateways; send the documented spelling.
    return {
        "Authorization": f"Bearer {token}",
        "Linkedin-Version": _normalize_linkedin_version(version),
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _resolve_author_urn(token: str, account: dict[str, Any], settings: Settings) -> str:
    configured = (account.get("author_urn") or settings.linkedin_author_urn or "").strip()
    if configured:
        if configured.startswith("urn:li:"):
            return configured
        if configured.isdigit():
            return f"urn:li:organization:{configured}"
        return f"urn:li:person:{configured}"
    response = requests.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            _linkedin_error(response, "resolve author")
            + " — set author_urn (urn:li:person:… or urn:li:organization:…) on the account"
        )
    sub = str((response.json() or {}).get("sub") or "").strip()
    if not sub:
        raise RuntimeError("LinkedIn userinfo did not return sub — set LINKEDIN_AUTHOR_URN")
    return f"urn:li:person:{sub}"


def _create_post(
    *,
    token: str,
    author_urn: str,
    commentary: str,
    apply_url: str | None,
    title: str,
    description: str,
    version: str,
) -> str:
    body: dict[str, Any] = {
        "author": author_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if apply_url and apply_url.startswith("http"):
        # LinkedIn card description should not contain the raw apply URL.
        # We keep the "Apply here:" line in commentary (plain text) and set
        # the card source explicitly via `content.article.source`.
        description_no_cta = _HOW_TO_APPLY_RE.sub("", description or "").strip()
        body["content"] = {
            "article": {
                "source": apply_url,
                "title": f"We're hiring: {title}"[:200],
                "description": re.sub(r"\s+", " ", description_no_cta).strip()[:256],
            }
        }
    response = _post_with_version_fallback(token=token, version=version, body=body)
    if response.status_code in (400, 422) and apply_url and "content" in body:
        # Some apps can post text but not article cards — fall back to text-only.
        body.pop("content", None)
        response = _post_with_version_fallback(token=token, version=version, body=body)
    if response.status_code >= 400:
        raise RuntimeError(_linkedin_error(response, "create post"))
    post_urn = (
        response.headers.get("x-restli-id")
        or response.headers.get("X-RestLi-Id")
        or ""
    ).strip()
    if not post_urn:
        location = (
            response.headers.get("location") or response.headers.get("Location") or ""
        ).strip()
        if "/posts/" in location:
            post_urn = location.split("/posts/")[-1].strip()
        elif location:
            post_urn = location
    if not post_urn:
        try:
            post_urn = str((response.json() or {}).get("id") or "").strip()
        except Exception:  # noqa: BLE001
            post_urn = ""
    return unquote(post_urn) or "posted"


def linkedin_post_view_url(post_urn: str | None) -> str | None:
    """Public feed URL for a Posts API share/ugcPost/activity URN."""
    raw = unquote((post_urn or "").strip())
    if not raw or raw.lower() == "posted":
        return None
    if "/posts/" in raw:
        raw = raw.split("/posts/")[-1]
    raw = raw.strip().strip("/")
    if raw.isdigit():
        raw = f"urn:li:share:{raw}"
    if not raw.startswith("urn:li:"):
        return None
    return f"https://www.linkedin.com/feed/update/{raw}"


def _current_linkedin_yyyymm() -> str:
    now = datetime.now(UTC)
    return f"{now.year}{now.month:02d}"


def _normalize_linkedin_version(version: str | None) -> str:
    """YYYYMM only. LinkedIn reports sunset versions as YYYYMMDD (e.g. 20250401)."""
    raw = re.sub(r"\D", "", (version or "").strip())
    if len(raw) >= 6:
        raw = raw[:6]
    else:
        return _current_linkedin_yyyymm()
    month = int(raw[4:6])
    if month < 1 or month > 12:
        return _current_linkedin_yyyymm()
    year = int(raw[:4])
    now = datetime.now(UTC)
    age_months = (now.year - year) * 12 + (now.month - month)
    # Versions older than ~11 months are sunset; bump to the current month.
    if age_months > 11 or age_months < -1:
        return _current_linkedin_yyyymm()
    return raw


def _rolling_linkedin_versions(count: int = 8) -> list[str]:
    now = datetime.now(UTC)
    year, month = now.year, now.month
    out: list[str] = []
    for _ in range(count):
        out.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return out


def _version_candidates(version: str | None) -> list[str]:
    configured = _normalize_linkedin_version(version)
    ordered = [configured, *_rolling_linkedin_versions()]
    out: list[str] = []
    for item in ordered:
        if item not in out:
            out.append(item)
    return out


def _post_with_version_fallback(
    *, token: str, version: str | None, body: dict[str, Any]
) -> requests.Response:
    last_response: requests.Response | None = None
    for candidate_version in _version_candidates(version):
        response = requests.post(
            POSTS_URL,
            headers=_auth_headers(token, candidate_version),
            json=body,
            timeout=30,
        )
        last_response = response
        if response.status_code != 426:
            if candidate_version != _normalize_linkedin_version(version):
                logger.info("LinkedIn post succeeded with version %s", candidate_version)
            return response
        logger.warning(
            "LinkedIn version %s is not active (426); trying a newer month",
            candidate_version,
        )
    assert last_response is not None
    return last_response


def _build_commentary(job: JobDescription, apply_url: str | None) -> str:
    apply_line = f"Apply here: {apply_url}" if apply_url else ""

    parts = [f"We're hiring: {job.title.strip()}"]
    # Avoid including the apply CTA (raw Google Form URL) in the description
    # we paste into commentary; we add it once via the dedicated "Apply here"
    # line.
    desc_clean = _HOW_TO_APPLY_RE.sub("", job.description_text or "").strip()
    desc = re.sub(r"\s+", " ", desc_clean)
    if desc:
        parts.append(desc[:1200])
    req = re.sub(r"\s+", " ", (job.requirements_text or "").strip())
    if req:
        parts.append(f"Requirements: {req[:600]}")

    base_text = "\n\n".join(parts).strip()

    if not apply_line:
        text = base_text
        if len(text) > COMMENTARY_MAX:
            text = text[: COMMENTARY_MAX - 1] + "…"
        return text

    # Ensure the apply line is never truncated away.
    glue = "\n\n"
    max_base = COMMENTARY_MAX - len(glue) - len(apply_line) - 1  # reserve 1 char for ellipsis
    if len(base_text) > max_base:
        base_text = base_text[: max_base - 1].rstrip() + "…"

    return (base_text + glue + apply_line).strip()


def _linkedin_error(response: requests.Response, action: str) -> str:
    detail = response.text.strip()[:400]
    try:
        payload = response.json()
        detail = str(payload.get("message") or payload.get("error_description") or detail)
    except Exception:  # noqa: BLE001
        pass
    return f"LinkedIn {action} failed ({response.status_code}): {detail}"
