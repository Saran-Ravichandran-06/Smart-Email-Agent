from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmailBase(BaseModel):
    gmail_message_id: str
    gmail_history_id: str | None = None
    thread_id: str
    sender: str
    recipient: str | None = None
    cc: str | None = None
    label_ids: str | None = None
    subject: str
    body: str
    priority: str | None = None
    summary: str | None = None
    task_extracted_at: datetime | None = None
    followup_evaluated_at: datetime | None = None
    gmail_synced_at: datetime | None = None
    gmail_deleted_at: datetime | None = None
    reply_sent_message_id: str | None = None
    reply_sent_thread_id: str | None = None
    reply_sent_at: datetime | None = None
    received_at: datetime
    user_id: int


class EmailCreate(EmailBase):
    pass


class EmailResponse(EmailBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
