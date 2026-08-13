"""Fetches CV submissions from HR webmail via IMAP (SSL).

Configured for mail.kafi-group.com / hr@kafi-group.com — FEATURE_CV_SCREENING.md §11.
Uses stdlib imaplib; marks processed UIDs in a local state file so Sync does
not re-download. Shared CV classifier skips non-CV PDF/DOCX.
"""
from __future__ import annotations

import datetime as dt
import email
import email.header
import email.utils
import imaplib
import json
import logging
import re
import socket
import ssl
from email.message import Message
from pathlib import Path

from app.core.config import Settings
from app.ingestion.cv_classifier import CV_EXTENSIONS, classify_cv_document
from app.ingestion.cv_submission import CvSubmission, SourceFetchResult

logger = logging.getLogger(__name__)

MAX_MESSAGES_PER_RUN = 30
LOOKBACK_DAYS = 30
STATE_FILENAME = "imap_processed_uids.json"


def _create_connection_ipv4(address: tuple[str, int], timeout: float | None) -> socket.socket:
    """Prefer IPv4 — Railway/containers often have no IPv6 route (Errno 101)."""
    host, port = address
    errors: list[OSError] = []
    for family, socktype, proto, _canon, sockaddr in socket.getaddrinfo(
        host, port, socket.AF_INET, socket.SOCK_STREAM
    ):
        sock: socket.socket | None = None
        try:
            sock = socket.socket(family, socktype, proto)
            if timeout is not None:
                sock.settimeout(timeout)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            errors.append(exc)
            if sock is not None:
                sock.close()
    if errors:
        raise errors[0]
    raise OSError(f"No IPv4 address for {host}:{port}")


class IMAP4_SSL_IPv4(imaplib.IMAP4_SSL):
    """IMAP4_SSL that never tries AAAA / IPv6 first."""

    def _create_socket(self, timeout):  # noqa: ANN001 — matches imaplib signature
        sock = _create_connection_ipv4((self.host, self.port), timeout)
        context = self.ssl_context if getattr(self, "ssl_context", None) else ssl.create_default_context()
        return context.wrap_socket(sock, server_hostname=self.host)


class IMAP4_IPv4(imaplib.IMAP4):
    def _create_socket(self, timeout):  # noqa: ANN001
        return _create_connection_ipv4((self.host, self.port), timeout)


def fetch_imap_submissions(settings: Settings) -> SourceFetchResult:
    """Never raises — returns SourceFetchResult for sync aggregation."""
    host = (settings.imap_host or "").strip()
    user = (settings.imap_user or "").strip()
    password = settings.imap_password or ""
    port = int(settings.imap_port or 993)

    if not host or not user or not password.strip():
        return SourceFetchResult(
            source="webmail",
            configured=False,
            submissions=[],
            message=(
                "Webmail IMAP not configured — set IMAP_HOST, IMAP_USER, and IMAP_PASSWORD "
                "(mail.kafi-group.com / hr@kafi-group.com)."
            ),
        )

    try:
        submissions = _fetch(settings, host, port, user, password)
        return SourceFetchResult(source="webmail", configured=True, submissions=submissions)
    except TimeoutError as exc:
        logger.warning("IMAP connect timed out to %s:%s — %s", host, port, exc)
        return SourceFetchResult(
            source="webmail",
            configured=True,
            submissions=[],
            message=(
                f"Webmail IMAP timed out connecting to {host}:{port}. "
                "This network is likely blocking outbound IMAP (common on local ISP/firewall). "
                "Use Sync CVs on the deployed Railway backend (or allow TCP 993), "
                "not from a blocked local machine."
            ),
        )
    except OSError as exc:
        # Connection refused / unreachable / no IPv6 route
        err = str(exc).lower()
        errno = getattr(exc, "errno", None)
        if (
            "timed out" in err
            or "unreachable" in err
            or errno in (101, 10060, 10061)
            or "10060" in err
            or "10061" in err
        ):
            logger.warning("IMAP network error to %s:%s — %s", host, port, exc)
            return SourceFetchResult(
                source="webmail",
                configured=True,
                submissions=[],
                message=(
                    f"Webmail IMAP cannot reach {host}:{port} ({exc}). "
                    "If this is Railway: ensure mail DNS uses a direct (non-proxied) A record "
                    "for IMAP, and IMAP_PASSWORD has no surrounding quotes."
                ),
            )
        logger.exception("IMAP fetch failed")
        return SourceFetchResult(
            source="webmail",
            configured=True,
            submissions=[],
            message=f"Webmail IMAP fetch failed: {exc}",
        )
    except imaplib.IMAP4.error as exc:
        logger.warning("IMAP auth/fetch failed: %s", exc)
        return SourceFetchResult(
            source="webmail",
            configured=False,
            submissions=[],
            message=f"Webmail IMAP login/fetch failed: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("IMAP fetch failed")
        return SourceFetchResult(
            source="webmail",
            configured=True,
            submissions=[],
            message=f"Webmail IMAP fetch failed: {exc}",
        )


def _fetch(
    settings: Settings, host: str, port: int, user: str, password: str
) -> list[CvSubmission]:
    # Avoid hanging Sync for ~60s when the host blocks this network (common on local ISP/firewall).
    timeout_s = 20.0
    # Force IPv4: mail.kafi-group.com has Cloudflare AAAA records; Railway often
    # cannot route IPv6 → "[Errno 101] Network is unreachable".
    if settings.imap_ssl:
        client: imaplib.IMAP4 = IMAP4_SSL_IPv4(host, port, timeout=timeout_s)
    else:
        client = IMAP4_IPv4(host, port, timeout=timeout_s)

    try:
        client.login(user, password)
        typ, _ = client.select("INBOX")
        if typ != "OK":
            raise RuntimeError("Could not select INBOX")

        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=LOOKBACK_DAYS)).strftime(
            "%d-%b-%Y"
        )
        typ, data = client.search(None, "SINCE", since)
        if typ != "OK":
            return []

        uids = data[0].split() if data and data[0] else []
        # Newest first
        uids = list(reversed(uids))[-MAX_MESSAGES_PER_RUN:]

        state = _load_state(settings)
        mailbox_key = f"{user}@{host}"
        done: set[str] = set(state.get(mailbox_key, []))
        submissions: list[CvSubmission] = []

        for uid in uids:
            uid_s = uid.decode() if isinstance(uid, bytes) else str(uid)
            if uid_s in done:
                continue

            typ, msg_data = client.fetch(uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                done.add(uid_s)
                continue

            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                done.add(uid_s)
                continue

            msg = email.message_from_bytes(bytes(raw))
            submission = _message_to_submission(msg, uid_s, settings)
            done.add(uid_s)
            if submission:
                submissions.append(submission)

        state[mailbox_key] = sorted(done)[-5000:]  # cap growth
        _save_state(settings, state)
        return submissions
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001
            pass


def _message_to_submission(
    msg: Message, uid: str, settings: Settings
) -> CvSubmission | None:
    filename, file_bytes = _first_cv_attachment(msg)
    if not file_bytes or not filename:
        return None

    classification = classify_cv_document(
        filename=filename, content=file_bytes, settings=settings
    )
    if not classification.is_cv:
        logger.info("IMAP uid %s skipped (not a CV): %s", uid, classification.reason)
        return None

    from_hdr = msg.get("From", "")
    sender_name, sender_email = email.utils.parseaddr(from_hdr)
    subject = _decode_header(msg.get("Subject", ""))
    date_hdr = msg.get("Date")
    body_text = _plain_body(msg)

    message_id = (msg.get("Message-ID") or "").strip() or f"imap-uid-{uid}"

    return CvSubmission(
        full_name=(sender_name or "").strip()
        or (sender_email.split("@")[0] if sender_email else "Unknown"),
        email=(sender_email or "").strip().lower() or None,
        phone=_extract_phone(body_text),
        position_hint=subject.strip() or "Unspecified",
        source="webmail",
        source_ref=message_id,
        cv_filename=filename,
        cv_bytes=file_bytes,
        submitted_at=_parse_date(date_hdr),
        raw_context_text=f"Subject: {subject}\n\n{body_text}",
    )


def _first_cv_attachment(msg: Message) -> tuple[str | None, bytes | None]:
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            continue
        filename = _decode_header(filename)
        suffix = Path(filename).suffix.lower()
        if suffix not in CV_EXTENSIONS:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
        return safe, payload
    return None, None


def _plain_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="ignore")
        return ""
    payload = msg.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="ignore")
    return str(msg.get_payload() or "")


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out: list[str] = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="ignore"))
        else:
            out.append(chunk)
    return "".join(out)


def _extract_phone(text: str) -> str | None:
    match = re.search(r"(\+?\d[\d\s\-]{8,14}\d)", text or "")
    return match.group(1).strip() if match else None


def _parse_date(raw: str | None) -> dt.datetime:
    if not raw:
        return dt.datetime.now(dt.timezone.utc)
    try:
        return email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return dt.datetime.now(dt.timezone.utc)


def _state_path(settings: Settings) -> Path:
    return settings.data_dir / STATE_FILENAME


def _load_state(settings: Settings) -> dict:
    path = _state_path(settings)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save_state(settings: Settings, state: dict) -> None:
    path = _state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")
