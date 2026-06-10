import re
from typing import Literal

from pydantic import BaseModel, Field

from app.processing.cleaner import remove_email_signatures, remove_quoted_replies
from app.utils.text import (
    decode_text,
    normalize_whitespace,
    remove_repeated_separators,
    strip_html,
)

ReplyTone = Literal["formal", "neutral", "friendly"]
REPLY_TONES = ("formal", "neutral", "friendly")

REPLY_SYSTEM = "Write concise professional email replies. Output only the reply body."

TONE_INSTRUCTIONS = {
    "formal": "Formal",
    "neutral": "Neutral",
    "friendly": "Friendly",
}

MAX_CURRENT_BODY_CHARS = 700
MAX_PRIOR_BODY_CHARS = 250
MAX_REPLY_PROMPT_CHARS = 1400
MAX_REPLY_OUTPUT_TOKENS = 120
MAX_REPLY_CHARS = 900
MIN_REPLY_CHARS = 20


class ThreadMessageSnippet(BaseModel):
    sender: str
    subject: str
    body: str


class ReplyGenerationContext(BaseModel):
    current: ThreadMessageSnippet
    prior_messages: list[ThreadMessageSnippet] = Field(default_factory=list)
    tone: ReplyTone = "neutral"


def normalize_tone(tone: str | None) -> ReplyTone:
    value = (tone or "neutral").strip().lower()
    if value not in REPLY_TONES:
        raise ValueError(f"Invalid tone. Use one of: {', '.join(REPLY_TONES)}")
    return value  # type: ignore[return-value]


def truncate_text(text: str, max_chars: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."


def clean_email_for_reply(text: str) -> str:
    if not text:
        return ""

    cleaned = decode_text(text)
    cleaned = strip_html(cleaned)
    cleaned = decode_text(cleaned)
    cleaned = remove_quoted_replies(cleaned)
    cleaned = remove_email_signatures(cleaned)
    cleaned = remove_reply_headers_and_footers(cleaned)
    cleaned = remove_repeated_separators(cleaned)
    cleaned = normalize_whitespace(cleaned)
    return cleaned


def remove_reply_headers_and_footers(text: str) -> str:
    if not text:
        return ""

    cleaned = text
    footer_patterns = [
        r"\n\s*confidentiality notice:.*$",
        r"\n\s*this message and any attachments.*$",
        r"\n\s*this email and any attachments.*$",
        r"\n\s*please consider the environment before printing.*$",
        r"\n\s*unsubscribe.*$",
    ]
    for pattern in footer_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if re.match(r"^(from|sent|to|cc|bcc|subject|date):\s+", stripped, re.IGNORECASE):
            continue
        lines.append(line)

    return "\n".join(lines).strip()


def build_reply_prompt(context: ReplyGenerationContext) -> str:
    tone_label = TONE_INSTRUCTIONS[context.tone]
    current_body = truncate_text(clean_email_for_reply(context.current.body), MAX_CURRENT_BODY_CHARS)

    parts = [
        "Write a short professional email reply.",
        f"Tone: {tone_label}",
    ]

    if context.prior_messages:
        prior = context.prior_messages[-1]
        prior_body = truncate_text(clean_email_for_reply(prior.body), MAX_PRIOR_BODY_CHARS)
        if prior_body:
            parts.extend(["Previous:", prior_body])

    parts.extend(["Email:", current_body, "Reply:"])
    return enforce_prompt_length("\n".join(parts))


def enforce_prompt_length(prompt: str) -> str:
    if len(prompt) <= MAX_REPLY_PROMPT_CHARS:
        return prompt

    overflow = len(prompt) - MAX_REPLY_PROMPT_CHARS
    email_marker = "\nEmail:\n"
    marker_index = prompt.find(email_marker)
    if marker_index == -1:
        return truncate_text(prompt, MAX_REPLY_PROMPT_CHARS)

    prefix = prompt[: marker_index + len(email_marker)]
    body_and_suffix = prompt[marker_index + len(email_marker) :]
    reply_marker = "\nReply:"
    reply_index = body_and_suffix.rfind(reply_marker)
    if reply_index == -1:
        return truncate_text(prompt, MAX_REPLY_PROMPT_CHARS)

    body = body_and_suffix[:reply_index]
    suffix = body_and_suffix[reply_index:]
    target_body_chars = max(200, len(body) - overflow - 3)
    return f"{prefix}{truncate_text(body, target_body_chars)}{suffix}"


_SUBJECT_PREFIX = re.compile(r"^subject:\s*.+\n?", re.IGNORECASE | re.MULTILINE)
_MARKDOWN_FENCE = re.compile(r"^```[\w]*\n?|\n?```$", re.MULTILINE)


def clean_reply_draft(text: str) -> str:
    if not text:
        return ""

    draft = text.strip()
    draft = _MARKDOWN_FENCE.sub("", draft)
    draft = _SUBJECT_PREFIX.sub("", draft).strip()

    if draft.lower().startswith("reply:"):
        draft = draft[6:].strip()

    draft = re.sub(r"\n{3,}", "\n\n", draft).strip()

    if len(draft) > MAX_REPLY_CHARS:
        draft = draft[:MAX_REPLY_CHARS].rstrip() + "..."

    return draft


def is_reply_too_short(text: str) -> bool:
    return len(text.strip()) < MIN_REPLY_CHARS


def looks_hallucinated(text: str, source_body: str) -> bool:
    """Flag replies that mention attachments/meetings when the source email did not."""
    source_lower = source_body.lower()
    text_lower = text.lower()
    if "attach" in text_lower and "attach" not in source_lower:
        return True
    if "attachment" in text_lower and "attachment" not in source_lower:
        return True
    if "scheduled" in text_lower and "schedul" not in source_lower:
        return True
    return False


def is_repetitive(new_text: str, previous_text: str | None) -> bool:
    if not previous_text:
        return False
    return normalize_for_compare(new_text) == normalize_for_compare(previous_text)


def normalize_for_compare(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
