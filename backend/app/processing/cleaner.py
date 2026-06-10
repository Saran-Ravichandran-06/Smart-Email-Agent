import re

from app.utils.text import (
    decode_text,
    normalize_whitespace,
    remove_repeated_separators,
    strip_html,
)

_SIGNATURE_PATTERNS = [
    re.compile(r"^--\s*\n", re.MULTILINE),
    re.compile(r"^Sent from my (iPhone|iPad|Android).*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Get Outlook for .*$", re.IGNORECASE | re.MULTILINE),
]

_QUOTED_REPLY_PATTERNS = [
    re.compile(r"^>+.*$", re.MULTILINE),
    re.compile(
        r"^On .+ wrote:\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^From:\s.+?\nSent:\s.+?\nTo:\s.+?\nSubject:\s.+$",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ),
]


def remove_email_signatures(text: str) -> str:
    if not text:
        return ""

    result = text
    for pattern in _SIGNATURE_PATTERNS:
        match = pattern.search(result)
        if match:
            result = result[: match.start()].rstrip()
    return result


def remove_quoted_replies(text: str) -> str:
    if not text:
        return ""

    result = text
    for pattern in _QUOTED_REPLY_PATTERNS:
        match = pattern.search(result)
        if match:
            result = result[: match.start()].rstrip()

    lines = []
    for line in result.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        lines.append(line)

    return "\n".join(lines).strip()


def clean_email_body(raw_body: str) -> str:
    """Deterministic plain-text cleaning pipeline for AI-ready output."""
    if not raw_body or not raw_body.strip():
        return ""

    text = decode_text(raw_body)
    text = strip_html(text)
    text = decode_text(text)
    text = remove_quoted_replies(text)
    text = remove_email_signatures(text)
    text = remove_repeated_separators(text)
    text = normalize_whitespace(text)

    return text[:12000] if text else ""
