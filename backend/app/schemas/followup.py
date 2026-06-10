from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FollowUpTaskInfo(BaseModel):
    id: int
    task_text: str
    status: str


class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    thread_id: str
    last_activity: datetime
    needs_followup: bool
    reason: str | None
    status: str
    draft_text: str | None
    resolved_at: datetime | None
    latest_email_id: int | None
    latest_email_sender: str | None = None
    latest_email_subject: str | None = None
    task_count: int = 0
    pending_task_count: int = 0
    completed_task_count: int = 0
    task_status_summary: str | None = None
    tasks: list[FollowUpTaskInfo] = Field(default_factory=list)
    priority_snapshot: str | None
    created_at: datetime


class FollowUpScanResponse(BaseModel):
    message: str
    scanned_threads: int
    created: int
    updated: int
    skipped: int
    cleared: int
    followup_ids: list[int]


class FollowUpDraftResponse(BaseModel):
    followup_id: int
    thread_id: str
    draft: str
    message: str


class FollowUpResolveResponse(BaseModel):
    followup_id: int
    status: str
    message: str = Field(default="Follow-up marked as resolved.")
