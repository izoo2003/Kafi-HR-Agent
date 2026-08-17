"""Supabase Storage helpers for employee / referral document files.

Uses the Storage HTTP API so both legacy JWT service_role keys and newer
`sb_secret_…` keys work. DB rows store: supabase://{bucket}/{object_path}.

Legacy local disk paths still resolve for older rows.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import requests

from app.core.config import Settings, get_settings
from app.core.exceptions import EntityNotFound, ValidationFailed

logger = logging.getLogger(__name__)

STORAGE_URI_PREFIX = "supabase://"


def storage_configured(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    url = (s.supabase_url or "").strip()
    key = (s.supabase_secret_key or "").strip()
    if not url or not key or "YOUR_PROJECT" in url:
        return False
    if key.startswith("sb_secret_...") or key.startswith("your_"):
        return False
    return True


def is_supabase_uri(path: str | None) -> bool:
    return bool(path) and str(path).startswith(STORAGE_URI_PREFIX)


def make_storage_uri(bucket: str, object_path: str) -> str:
    object_path = object_path.lstrip("/")
    return f"{STORAGE_URI_PREFIX}{bucket}/{object_path}"


def parse_storage_uri(uri: str) -> tuple[str, str]:
    raw = uri.removeprefix(STORAGE_URI_PREFIX)
    bucket, _, object_path = raw.partition("/")
    if not bucket or not object_path:
        raise ValidationFailed(f"Invalid Supabase storage URI: {uri}")
    return bucket, object_path


def _base_url(settings: Settings) -> str:
    return settings.supabase_url.strip().rstrip("/")


def _headers(settings: Settings, *, content_type: str | None = None) -> dict[str, str]:
    key = settings.supabase_secret_key.strip()
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _raise_for_storage(resp: requests.Response, *, action: str) -> None:
    if resp.ok:
        return
    detail = resp.text[:500] if resp.text else resp.reason
    if resp.status_code == 404:
        raise EntityNotFound(f"File not found in Supabase Storage ({action}): {detail}")
    raise ValidationFailed(f"Supabase Storage {action} failed ({resp.status_code}): {detail}")


def ensure_employee_documents_bucket(settings: Settings | None = None) -> str:
    """Create the private employee-documents bucket if missing. Returns bucket name."""
    s = settings or get_settings()
    bucket = (s.supabase_storage_bucket or "employee-documents").strip() or "employee-documents"
    if not storage_configured(s):
        return bucket

    base = _base_url(s)
    try:
        list_resp = requests.get(
            f"{base}/storage/v1/bucket",
            headers=_headers(s),
            timeout=30,
        )
        if list_resp.ok:
            existing: set[str] = set()
            for item in list_resp.json() or []:
                if isinstance(item, dict) and item.get("id"):
                    existing.add(str(item["id"]))
                elif isinstance(item, dict) and item.get("name"):
                    existing.add(str(item["name"]))
            if bucket in existing:
                return bucket

        create_resp = requests.post(
            f"{base}/storage/v1/bucket",
            headers=_headers(s, content_type="application/json"),
            json={
                "id": bucket,
                "name": bucket,
                "public": False,
                "file_size_limit": 15 * 1024 * 1024,
            },
            timeout=30,
        )
        # 200/201 created; 409 already exists
        if create_resp.status_code in {200, 201}:
            logger.info("Created Supabase Storage bucket %s", bucket)
        elif create_resp.status_code not in {409}:
            logger.warning(
                "Could not create Storage bucket %s: %s %s",
                bucket,
                create_resp.status_code,
                create_resp.text[:300],
            )
    except requests.RequestException as exc:
        logger.warning("Could not ensure Storage bucket %s: %s", bucket, exc)
    return bucket


def upload_bytes(
    *,
    object_path: str,
    content: bytes,
    content_type: str | None,
    settings: Settings | None = None,
) -> str:
    """Upload bytes to the configured bucket; returns supabase:// URI for DB storage."""
    s = settings or get_settings()
    if not storage_configured(s):
        raise ValidationFailed("Supabase Storage is not configured")
    bucket = ensure_employee_documents_bucket(s)
    object_path = object_path.lstrip("/")
    mime = content_type or "application/octet-stream"
    # Encode each path segment but keep slashes
    encoded = "/".join(quote(seg, safe="") for seg in object_path.split("/"))
    url = f"{_base_url(s)}/storage/v1/object/{bucket}/{encoded}"
    headers = _headers(s, content_type=mime)
    headers["x-upsert"] = "true"
    try:
        resp = requests.post(url, headers=headers, data=content, timeout=60)
        if resp.status_code in {200, 201}:
            return make_storage_uri(bucket, object_path)
        # Some projects prefer PUT for upsert
        if resp.status_code in {400, 409}:
            resp = requests.put(url, headers=headers, data=content, timeout=60)
        _raise_for_storage(resp, action="upload")
    except requests.RequestException as exc:
        raise ValidationFailed(f"Failed to upload file to Supabase Storage: {exc}") from exc
    return make_storage_uri(bucket, object_path)


def download_bytes(uri: str) -> bytes:
    s = get_settings()
    if not storage_configured(s):
        raise EntityNotFound("Supabase Storage is not configured")
    bucket, object_path = parse_storage_uri(uri)
    encoded = "/".join(quote(seg, safe="") for seg in object_path.split("/"))
    url = f"{_base_url(s)}/storage/v1/object/{bucket}/{encoded}"
    try:
        resp = requests.get(url, headers=_headers(s), timeout=60)
        _raise_for_storage(resp, action="download")
    except requests.RequestException as exc:
        raise EntityNotFound(f"File not found in Supabase Storage: {exc}") from exc
    if not resp.content:
        raise EntityNotFound("File not found in Supabase Storage")
    return resp.content


def delete_object(uri: str) -> None:
    if not is_supabase_uri(uri):
        return
    s = get_settings()
    if not storage_configured(s):
        return
    bucket, object_path = parse_storage_uri(uri)
    url = f"{_base_url(s)}/storage/v1/object/{bucket}"
    try:
        resp = requests.delete(
            url,
            headers=_headers(s, content_type="application/json"),
            json={"prefixes": [object_path]},
            timeout=30,
        )
        # Alternate body shape used by some API versions
        if not resp.ok:
            resp = requests.delete(
                url,
                headers=_headers(s, content_type="application/json"),
                json=[object_path],
                timeout=30,
            )
        if not resp.ok:
            logger.warning("Failed to delete Supabase object %s: %s %s", uri, resp.status_code, resp.text[:200])
    except requests.RequestException as exc:
        logger.warning("Failed to delete Supabase object %s: %s", uri, exc)
