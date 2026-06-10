from pydantic import BaseModel, Field

from app.ai.classification import PRIORITY_LABELS


class PriorityClassificationResponse(BaseModel):
    email_id: int
    gmail_message_id: str
    classified: bool
    priority: str | None
    message: str


class BatchPriorityClassificationResponse(BaseModel):
    message: str
    classified: int
    skipped: int
    failed: int
    results: list[PriorityClassificationResponse]


class EmailListByPriorityParams(BaseModel):
    priority: str = Field(..., description=f"One of: {', '.join(PRIORITY_LABELS)}")
