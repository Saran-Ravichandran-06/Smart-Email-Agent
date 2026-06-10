import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any

from app.processing.cleaner import clean_email_body
from app.utils.text import decode_text, normalize_whitespace, strip_html


@dataclass(frozen=True)
class ParsedGmailMessage:
    gmail_message_id: str
    gmail_history_id: str | None
    thread_id: str
    sender: str
    recipient: str | None
    cc: str | None
    subject: str
    body_raw: str
    body_cleaned: str
    label_ids: str | None
    received_at: datetime


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    target = name.lower()
    for header in headers:
        if header.get("name", "").lower() == target:
            return header.get("value", "").strip()
    return ""


def _parse_sender(raw_from: str) -> str:
    if not raw_from:
        return "Unknown Sender"
    name, address = parseaddr(raw_from)
    if name and address:
        return f"{name} <{address}>"
    return address or name or raw_from


def _clean_header_value(value: str) -> str | None:
    cleaned = normalize_whitespace(decode_text(value or ""))
    return cleaned or None


def _decode_body_data(data: str | None) -> str:
    if not data:
        return ""
    try:
        padding = "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode(data + padding)
        return decoded.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def _extract_mime_bodies(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    plain_bodies: list[str] = []
    html_bodies: list[str] = []

    mime_type = (payload.get("mimeType") or "").lower()
    body_data = payload.get("body", {}).get("data")
    if body_data and mime_type in {"text/plain", "text/html"}:
        text = _decode_body_data(body_data)
        if text and mime_type == "text/plain":
            plain_bodies.append(text)
        elif text and mime_type == "text/html":
            html_bodies.append(text)

    parts = payload.get("parts") or []
    for part in parts:
        child_plain, child_html = _extract_mime_bodies(part)
        plain_bodies.extend(child_plain)
        html_bodies.extend(child_html)

    return plain_bodies, html_bodies


def _extract_best_body(payload: dict[str, Any], snippet: str) -> tuple[str, str]:
    plain_bodies, html_bodies = _extract_mime_bodies(payload)

    if plain_bodies:
        raw = normalize_whitespace("\n\n".join(plain_bodies))
        return raw, clean_email_body(raw)

    if html_bodies:
        html_body = "\n\n".join(html_bodies)
        raw = normalize_whitespace(decode_text(strip_html(html_body)))
        return raw, clean_email_body(raw)

    fallback = normalize_whitespace(decode_text(snippet))
    return fallback, clean_email_body(fallback)


def _serialize_label_ids(message: dict[str, Any]) -> str | None:
    label_ids = message.get("labelIds") or []
    if not label_ids:
        return None
    return json.dumps(label_ids)


def parse_received_at(message: dict[str, Any]) -> datetime:
    internal_date = message.get("internalDate")
    if internal_date:
        try:
            return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
        except (TypeError, ValueError):
            pass

    date_header = _get_header(message.get("payload", {}).get("headers", []), "Date")
    if date_header:
        try:
            from email.utils import parsedate_to_datetime

            parsed = parsedate_to_datetime(date_header)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            pass

    return datetime.now(timezone.utc)


def parse_gmail_message(message: dict[str, Any]) -> ParsedGmailMessage:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []

    sender = _parse_sender(_get_header(headers, "From"))
    recipient = _clean_header_value(_get_header(headers, "To"))
    cc = _clean_header_value(_get_header(headers, "Cc"))
    subject = _get_header(headers, "Subject") or "(No Subject)"
    snippet = (message.get("snippet") or "").strip()
    body_raw, body_cleaned = _extract_best_body(payload, snippet)
    if not body_raw:
        body_raw = "(No content)"

    return ParsedGmailMessage(
        gmail_message_id=message.get("id", ""),
        gmail_history_id=message.get("historyId"),
        thread_id=message.get("threadId", ""),
        sender=sender,
        recipient=recipient,
        cc=cc,
        subject=subject,
        body_raw=body_raw,
        body_cleaned=body_cleaned,
        label_ids=_serialize_label_ids(message),
        received_at=parse_received_at(message),
    )


def parse_thread_metadata(thread: dict[str, Any]) -> dict[str, Any]:
    messages = thread.get("messages") or []
    return {
        "thread_id": thread.get("id", ""),
        "history_id": thread.get("historyId"),
        "message_count": len(messages),
        "message_ids": [message.get("id") for message in messages if message.get("id")],
    }
