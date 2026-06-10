from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    email_id: int
    task_text: str
    deadline: datetime | None = None
    deadline_text: str | None = None
    status: str = "pending"


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., description="pending | in_progress | completed | cancelled")
