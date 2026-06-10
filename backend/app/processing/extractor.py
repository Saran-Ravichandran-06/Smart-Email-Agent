import base64
from typing import Any

from app.utils.text import strip_html


def decode_body_data(data: str | None) -> str:
    if not data:
        return ""
    try:
        padding = "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode(data + padding)
        return decoded.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    target = name.lower()
    for header in headers or []:
        if header.get("name", "").lower() == target:
            return header.get("value", "").strip()
    return ""


def extract_text_from_payload(payload: dict[str, Any] | None) -> str:
    """Extract readable text from a Gmail message payload (multipart-safe)."""
    if not payload:
        return ""

    mime_type = (payload.get("mimeType") or "").lower()
    parts = payload.get("parts") or []

    if parts:
        plain = _extract_by_mime(parts, "text/plain")
        if plain:
            return plain

        html = _extract_by_mime(parts, "text/html")
        if html:
            return strip_html(html)

        for part in parts:
            nested = extract_text_from_payload(part)
            if nested.strip():
                return nested

    body_data = payload.get("body", {}).get("data")
    decoded = decode_body_data(body_data)
    if not decoded:
        return ""

    if mime_type == "text/html" or decoded.lstrip().startswith("<"):
        return strip_html(decoded)
    return decoded


def _extract_by_mime(parts: list[dict[str, Any]], target_mime: str) -> str:
    chunks: list[str] = []
    for part in parts:
        mime_type = (part.get("mimeType") or "").lower()
        if mime_type == target_mime:
            decoded = decode_body_data(part.get("body", {}).get("data"))
            if decoded:
                chunks.append(decoded)
        nested_parts = part.get("parts") or []
        if nested_parts:
            nested = _extract_by_mime(nested_parts, target_mime)
            if nested:
                chunks.append(nested)
    return "\n\n".join(chunks).strip()


def extract_text_from_gmail_message(message: dict[str, Any]) -> str:
    snippet = (message.get("snippet") or "").strip()
    payload = message.get("payload") or {}
    body = extract_text_from_payload(payload)
    if body.strip():
        return body.strip()
    return snippet


def extract_metadata_from_gmail_message(message: dict[str, Any]) -> dict[str, str]:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []
    return {
        "gmail_message_id": message.get("id") or "",
        "thread_id": message.get("threadId") or "",
        "sender": _get_header(headers, "From"),
        "recipient": _get_header(headers, "To") or _get_header(headers, "Delivered-To"),
        "subject": _get_header(headers, "Subject"),
    }
