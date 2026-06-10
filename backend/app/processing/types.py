from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EmailMetadata:
    gmail_message_id: str
    thread_id: str
    sender: str
    recipient: str | None
    subject: str
    timestamp: datetime


@dataclass(frozen=True)
class ProcessedEmailContent:
    metadata: EmailMetadata
    body_raw: str
    body_cleaned: str
