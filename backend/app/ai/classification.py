from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

PRIORITY_LABELS = ("urgent", "important", "low", "noise")
PriorityLevel = Literal["urgent", "important", "low", "noise"]

CLASSIFICATION_SYSTEM = (
    "You classify email priority. Respond with valid JSON only. "
    'Use exactly one priority: urgent, important, low, noise.'
)

CLASSIFICATION_SCHEMA_HINT = '{"priority": "urgent|important|low|noise"}'

MAX_BODY_CHARS = 1200


class PriorityClassificationResult(BaseModel):
    priority: PriorityLevel


class EmailPriorityInput(BaseModel):
    sender: str
    subject: str
    body_cleaned: str = Field(..., min_length=1)


class ClassificationSkipReason(str, Enum):
    EMPTY_BODY = "empty_body"
    NOT_PROCESSED = "not_processed"


def truncate_body(body: str, max_chars: int = MAX_BODY_CHARS) -> str:
    text = body.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def build_classification_prompt(email_input: EmailPriorityInput) -> str:
    """Short, deterministic prompt for Phi-3."""
    body = truncate_body(email_input.body_cleaned)
    return (
        "Classify this email.\n"
        "urgent=immediate action; important=needs response; "
        "low=FYI; noise=promo/newsletter/automated.\n\n"
        f"From: {email_input.sender}\n"
        f"Subject: {email_input.subject}\n"
        f"Body: {body}\n\n"
        'Return JSON: {"priority": "urgent|important|low|noise"}'
    )


def normalize_priority(value: str) -> PriorityLevel:
    normalized = value.strip().lower()
    if normalized in PRIORITY_LABELS:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Invalid priority label: {value}")
