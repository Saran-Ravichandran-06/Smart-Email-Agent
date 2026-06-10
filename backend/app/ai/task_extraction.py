from pydantic import BaseModel, Field

EXTRACTION_SYSTEM = (
    "Extract actionable tasks from emails. Respond with valid JSON only. "
    "Include explicit tasks and strongly implied requests that require the recipient to act. "
    "Do not include newsletters, FYI updates, receipts, alerts, or vague suggestions. "
    'Use {"tasks": [{"task": "...", "deadline": "..."}]}. '
    "Use deadline null if none. Return empty tasks array if none."
)

EXTRACTION_SCHEMA_HINT = (
    '{"tasks": [{"task": "action description", "deadline": "Friday or null"}]}'
)

MAX_BODY_CHARS = 1200


class ExtractedTaskItem(BaseModel):
    task: str = Field(..., min_length=1)
    deadline: str | None = None


class TaskExtractionResult(BaseModel):
    tasks: list[ExtractedTaskItem] = Field(default_factory=list)


class EmailTaskInput(BaseModel):
    subject: str
    body_cleaned: str = Field(..., min_length=1)


def truncate_body(body: str, max_chars: int = MAX_BODY_CHARS) -> str:
    text = body.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def build_task_extraction_prompt(email_input: EmailTaskInput) -> str:
    body = truncate_body(email_input.body_cleaned)
    return (
        "Extract actionable tasks from this email.\n"
        "Include explicit tasks and strongly implied requests for the recipient.\n"
        "Skip FYI-only updates, newsletters, automated alerts, receipts, and vague suggestions.\n"
        "Use deadline as a short string (e.g. Friday, 2025-06-01) or null.\n\n"
        f"Subject: {email_input.subject}\n"
        f"Body: {body}\n\n"
        'Return JSON: {"tasks": [{"task": "...", "deadline": "..."}]}'
    )
