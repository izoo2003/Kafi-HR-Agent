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
import os
import re
import socket
import ssl
import struct
from email.message import Message
from pathlib import Path

from app.core.config import Settings
from app.ingestion.cv_classifier import CV_EXTENSIONS, AttachmentCandidate, pick_cv_attachment
from app.ingestion.cv_submission import CvSubmission, SourceFetchResult

logger = logging.getLogger(__name__)

MAX_MESSAGES_PER_RUN = 8
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
    """IMAP4_SSL that never tries AAAA / IPv6 first.

    `tls_server_name` is the SNI / certificate hostname (mail.kafi-group.com)
    when TCP connects to a different origin (MX / hosting IP) because the
    public mail hostname is Cloudflare-proxied.
    """

    def __init__(
        self,
        host: str = "",
        port: int = imaplib.IMAP4_SSL_PORT,
        *,
        timeout: float | None = None,
        tls_server_name: str | None = None,
    ):
        self._tls_server_name = tls_server_name or host
        super().__init__(host, port, timeout=timeout)

    def _create_socket(self, timeout):  # noqa: ANN001 — matches imaplib signature
        sock = _create_connection_ipv4((self.host, self.port), timeout)
        context = self.ssl_context if getattr(self, "ssl_context", None) else ssl.create_default_context()
        return context.wrap_socket(sock, server_hostname=self._tls_server_name)


class IMAP4_IPv4(imaplib.IMAP4):
    def _create_socket(self, timeout):  # noqa: ANN001
        return _create_connection_ipv4((self.host, self.port), timeout)


def _ipv4_list(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, 993, socket.AF_INET, socket.SOCK_STREAM)
    except OSError:
        return []
    ips: list[str] = []
    for *_, sockaddr in infos:
        ip = sockaddr[0]
        if ip not in ips:
            ips.append(ip)
    return ips


def _is_cloudflare_ipv4(ip: str) -> bool:
    """True when `ip` is in a published Cloudflare proxy range (orange-cloud)."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    if a == 104 and 16 <= b <= 31:
        return True
    if a == 172 and 64 <= b <= 71:
        return True
    if a == 188 and b == 114:
        return True
    if a == 162 and b == 158:
        return True
    if (a, b) in {(198, 41), (197, 234), (108, 162), (141, 101), (190, 93), (173, 245)}:
        return True
    return False


def _decode_dns_name(msg: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    jumped = False
    end = offset
    hops = 0
    while hops < 20 and offset < len(msg):
        hops += 1
        length = msg[offset]
        if length == 0:
            if not jumped:
                end = offset + 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(msg):
                break
            pointer = ((length & 0x3F) << 8) | msg[offset + 1]
            if not jumped:
                end = offset + 2
            offset = pointer
            jumped = True
            continue
        offset += 1
        labels.append(msg[offset : offset + length].decode("ascii", "ignore"))
        offset += length
        if not jumped:
            end = offset
    return ".".join(labels), end


def _system_dns_nameservers() -> list[str]:
    """Best-effort resolver list: platform resolv.conf first, then public DNS."""
    servers: list[str] = []
    try:
        resolv = Path("/etc/resolv.conf")
        if resolv.is_file():
            for line in resolv.read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0] == "nameserver":
                    ip = parts[1].strip()
                    if ip and ip not in servers:
                        servers.append(ip)
    except OSError:
        pass
    for fallback in ("8.8.8.8", "1.1.1.1", "8.8.4.4"):
        if fallback not in servers:
            servers.append(fallback)
    return servers


def _lookup_mx(domain: str, dns_server: str = "8.8.8.8") -> str | None:
    """Lowest-preference MX host via UDP DNS (stdlib only — no dnspython)."""
    labels = domain.strip(".").encode("ascii", "ignore").split(b".")
    if not labels or labels == [b""]:
        return None
    tid = int.from_bytes(os.urandom(2), "big")
    query = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    for lab in labels:
        query += bytes([len(lab)]) + lab
    query += b"\x00" + struct.pack("!HH", 15, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.sendto(query, (dns_server, 53))
        data, _ = sock.recvfrom(2048)
    except OSError:
        return None
    finally:
        sock.close()
    if len(data) < 12:
        return None
    rtid, flags, qdcount, ancount, _ns, _ar = struct.unpack("!HHHHHH", data[:12])
    if rtid != tid or (flags & 0x000F) != 0 or ancount == 0:
        return None
    offset = 12
    for _ in range(qdcount):
        _, offset = _decode_dns_name(data, offset)
        offset += 4
    best: tuple[int, str] | None = None
    for _ in range(ancount):
        _, offset = _decode_dns_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, _cls, _ttl, rdlen = struct.unpack("!HHIH", data[offset : offset + 10])
        offset += 10
        rdata_abs = offset
        offset += rdlen
        if rtype != 15 or rdlen < 3:
            continue
        pref = struct.unpack("!H", data[rdata_abs : rdata_abs + 2])[0]
        host, _ = _decode_dns_name(data, rdata_abs + 2)
        host = host.rstrip(".")
        if host and (best is None or pref < best[0]):
            best = (pref, host)
    return best[1] if best else None


def _lookup_mx_any(domain: str) -> str | None:
    for server in _system_dns_nameservers():
        found = _lookup_mx(domain, dns_server=server)
        if found:
            return found
    return None


def _known_mail_origin(domain: str) -> str | None:
    """Hard-coded origin MX when DNS lookup is unavailable (e.g. Railway UDP blocked)."""
    known = {
        "kafi-group.com": "_dc-mx.32098f035483.kafi-group.com",
    }
    return known.get(domain.strip().lower().rstrip("."))


def _imap_endpoint(settings: Settings, named_host: str) -> tuple[str, str]:
    """TCP host + TLS server name.

    `mail.kafi-group.com` is orange-clouded at Cloudflare, which only proxies
    HTTP — IMAP :993 to those IPs times out. Connect to the MX/origin instead
    and keep the public hostname for SNI so the certificate matches.
    """
    override = (getattr(settings, "imap_connect_host", "") or "").strip()
    sni = (getattr(settings, "imap_tls_server_name", "") or "").strip() or named_host
    if override:
        return override, sni
    ips = _ipv4_list(named_host)
    if ips and all(_is_cloudflare_ipv4(ip) for ip in ips):
        domain = named_host
        user = (settings.imap_user or "").strip()
        if "@" in user:
            domain = user.split("@", 1)[1]
        elif named_host.lower().startswith("mail."):
            domain = named_host[5:]
        mx = _lookup_mx_any(domain) or _known_mail_origin(domain)
        if mx:
            logger.warning(
                "IMAP host %s is Cloudflare-proxied; connecting via MX %s (TLS SNI %s)",
                named_host,
                mx,
                sni,
            )
            return mx, sni
        raise TimeoutError(
            f"{named_host} resolves only to Cloudflare proxy IPs; IMAP port 993 is not "
            "proxied. Grey-cloud that DNS record, or set IMAP_CONNECT_HOST to the origin "
            "mail server (MX hostname or hosting IP from SPF)."
        )
    return named_host, sni


def probe_imap_connection(settings: Settings) -> tuple[bool, str]:
    """Quick login test for startup / ops diagnostics. Never raises."""
    host = (settings.imap_host or "").strip()
    user = (settings.imap_user or "").strip()
    password = (settings.imap_password or "").strip()
    if not host or not user or not password:
        return False, "IMAP not configured — set IMAP_USER and IMAP_PASSWORD on Railway"
    client: imaplib.IMAP4 | None = None
    try:
        connect_host, tls_name = _imap_endpoint(settings, host)
        client = _open_imap_client(settings)
        client.logout()
        client = None
        return True, f"IMAP OK ({user} via {connect_host}, TLS SNI {tls_name})"
    except Exception as exc:  # noqa: BLE001
        return False, f"IMAP probe failed: {exc}"
    finally:
        if client is not None:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass


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
        detail = str(exc).strip()
        if "Cloudflare" in detail:
            message = detail
        else:
            message = (
                f"Webmail IMAP timed out connecting to {host}:{port}. "
                "If this hostname is orange-clouded in Cloudflare, set IMAP_CONNECT_HOST "
                "to the origin mail server (MX hostname or hosting IP) — IMAP is not "
                "proxied on port 993."
            )
        return SourceFetchResult(
            source="webmail",
            configured=True,
            submissions=[],
            message=message,
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


def _open_imap_client(settings: Settings) -> imaplib.IMAP4:
    host = (settings.imap_host or "").strip()
    user = (settings.imap_user or "").strip()
    password = settings.imap_password or ""
    port = int(settings.imap_port or 993)
    timeout_s = 20.0
    connect_host, tls_name = _imap_endpoint(settings, host)
    if settings.imap_ssl:
        client: imaplib.IMAP4 = IMAP4_SSL_IPv4(
            connect_host, port, timeout=timeout_s, tls_server_name=tls_name
        )
    else:
        client = IMAP4_IPv4(connect_host, port, timeout=timeout_s)
    client.login(user, password)
    return client


def _fetch(
    settings: Settings, host: str, port: int, user: str, password: str
) -> list[CvSubmission]:
    # Avoid hanging Sync for ~60s when the host blocks this network (common on local ISP/firewall).
    _ = (host, port, user, password)
    client = _open_imap_client(settings)

    try:
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
        # Newest first, cap to MAX_MESSAGES_PER_RUN
        uids = list(reversed(uids))[:MAX_MESSAGES_PER_RUN]

        state = _load_state(settings)
        mailbox_key = f"{user}@{host}"
        done: set[str] = set(state.get(mailbox_key, []))
        submissions: list[CvSubmission] = []

        for uid in uids:
            uid_s = uid.decode() if isinstance(uid, bytes) else str(uid)
            if uid_s in done:
                continue
            try:
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
            except Exception:
                logger.warning("IMAP skip uid %s", uid_s, exc_info=True)
                done.add(uid_s)
                continue

        state[mailbox_key] = sorted(done)[-5000:]  # cap growth
        _save_state(settings, state)
        return submissions
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001
            pass


def restore_imap_cv(message_id: str, settings: Settings) -> tuple[str, bytes] | None:
    """Re-download a webmail CV by Message-ID or imap-uid-{n}."""
    ref = (message_id or "").strip()
    host = (settings.imap_host or "").strip()
    user = (settings.imap_user or "").strip()
    password = settings.imap_password or ""
    if not ref or not host or not user or not password.strip():
        return None
    client: imaplib.IMAP4 | None = None
    try:
        client = _open_imap_client(settings)
        typ, _ = client.select("INBOX")
        if typ != "OK":
            return None
        uid = _imap_uid_from_ref(ref)
        if uid is None:
            uid = _search_imap_message_id(client, ref)
        if uid is None:
            return None
        typ, msg_data = client.fetch(uid.encode() if isinstance(uid, str) else uid, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            return None
        raw = msg_data[0][1]
        if not isinstance(raw, (bytes, bytearray)):
            return None
        msg = email.message_from_bytes(bytes(raw))
        filename, file_bytes = _best_cv_attachment(msg, settings)
        if file_bytes and filename:
            return filename, file_bytes
        return None
    except Exception:
        logger.warning("IMAP CV restore failed for %s", ref, exc_info=True)
        return None
    finally:
        if client is not None:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass


def _imap_uid_from_ref(ref: str) -> str | None:
    match = re.fullmatch(r"imap-uid-(\d+)", ref.strip(), flags=re.I)
    return match.group(1) if match else None


def _search_imap_message_id(client: imaplib.IMAP4, message_id: str) -> str | None:
    raw = message_id.strip()
    bare = raw.strip("<>").strip()
    candidates = [raw]
    if bare and f"<{bare}>" not in candidates:
        candidates.append(f"<{bare}>")
    if bare and bare not in candidates:
        candidates.append(bare)
    for value in candidates:
        quoted = value.replace("\\", "\\\\").replace('"', '\\"')
        for charset, query in (
            (None, ("HEADER", "Message-ID", value)),
            (None, ("HEADER", "Message-ID", f'"{quoted}"')),
        ):
            try:
                typ, data = client.search(charset, *query)
            except Exception:  # noqa: BLE001
                continue
            if typ != "OK" or not data or not data[0]:
                continue
            uids = data[0].split()
            if uids:
                uid = uids[-1]
                return uid.decode() if isinstance(uid, bytes) else str(uid)
    return None


def _message_to_submission(
    msg: Message, uid: str, settings: Settings
) -> CvSubmission | None:
    filename, file_bytes = _best_cv_attachment(msg, settings)
    if not file_bytes or not filename:
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


def _best_cv_attachment(msg: Message, settings: Settings) -> tuple[str | None, bytes | None]:
    candidates: list[AttachmentCandidate] = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        disp = (part.get("Content-Disposition") or "").lower()
        has_cid = bool(part.get("Content-ID"))
        is_inline = disp.startswith("inline") or (has_cid and "attachment" not in disp)
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
        candidates.append(AttachmentCandidate(filename=safe, content=payload, is_inline=is_inline))
    return pick_cv_attachment(candidates, settings, source="email")


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
