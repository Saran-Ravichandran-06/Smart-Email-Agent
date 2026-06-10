from datetime import datetime, timezone

from app.processing.cleaner import clean_email_body
from app.processing.extractor import extract_text_from_gmail_message
from app.processing.types import EmailMetadata, ProcessedEmailContent
from app.utils.text import normalize_whitespace
from email.utils import parseaddr


def _parse_address(raw_value: str) -> str:
    if not raw_value:
        return "Unknown Sender"
    name, address = parseaddr(raw_value)
    if name and address:
        return f"{name} <{address}>"
    return address or name or raw_value


def build_metadata(
    *,
    gmail_message_id: str,
    thread_id: str,
    sender: str,
    recipient: str | None,
    subject: str,
    timestamp: datetime,
) -> EmailMetadata:
    return EmailMetadata(
        gmail_message_id=gmail_message_id or "",
        thread_id=thread_id or "",
        sender=_parse_address(sender) if sender else "Unknown Sender",
        recipient=recipient or None,
        subject=normalize_whitespace(subject) or "(No Subject)",
        timestamp=timestamp,
    )


def process_raw_email_content(
    *,
    gmail_message_id: str,
    thread_id: str,
    sender: str,
    recipient: str | None,
    subject: str,
    timestamp: datetime,
    body_raw: str,
) -> ProcessedEmailContent:
    raw = (body_raw or "").strip()
    cleaned = clean_email_body(raw)

    if not cleaned and raw:
        cleaned = normalize_whitespace(raw)[:12000]

    metadata = build_metadata(
        gmail_message_id=gmail_message_id,
        thread_id=thread_id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        timestamp=timestamp,
    )

    return ProcessedEmailContent(
        metadata=metadata,
        body_raw=raw,
        body_cleaned=cleaned or "(Empty body)",
    )


def process_gmail_message(message: dict, *, fallback_timestamp: datetime | None = None) -> ProcessedEmailContent:
    from app.gmail.parser import parse_received_at

    payload = message.get("payload") or {}
    headers = payload.get("headers") or []

    def header(name: str) -> str:
        for item in headers:
            if item.get("name", "").lower() == name.lower():
                return (item.get("value") or "").strip()
        return ""

    timestamp = parse_received_at(message)
    if fallback_timestamp and not message.get("internalDate"):
        timestamp = fallback_timestamp

    body_raw = extract_text_from_gmail_message(message)

    return process_raw_email_content(
        gmail_message_id=message.get("id") or "",
        thread_id=message.get("threadId") or "",
        sender=header("From"),
        recipient=header("To") or header("Delivered-To") or None,
        subject=header("Subject"),
        timestamp=timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc),
        body_raw=body_raw,
    )
