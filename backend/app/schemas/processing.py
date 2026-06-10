from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmailMetadataResponse(BaseModel):
    gmail_message_id: str
    thread_id: str
    sender: str
    recipient: str | None
    cc: str | None = None
    subject: str
    timestamp: datetime


class EmailCleanedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    metadata: EmailMetadataResponse
    body_raw: str
    body_cleaned: str
    processed_at: datetime | None


class EmailProcessItemResult(BaseModel):
    email_id: int
    gmail_message_id: str
    processed: bool
    message: str


class EmailBatchProcessResponse(BaseModel):
    message: str
    processed: int
    skipped: int
    failed: int
    results: list[EmailProcessItemResult]
