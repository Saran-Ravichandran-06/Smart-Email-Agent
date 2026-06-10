from pydantic import BaseModel, Field


class TaskExtractionItemResponse(BaseModel):
    task_text: str
    created: bool
    message: str


class EmailTaskExtractionResponse(BaseModel):
    email_id: int
    gmail_message_id: str
    extracted: bool
    tasks_found: int
    tasks_created: int
    tasks_skipped: int
    message: str
    items: list[TaskExtractionItemResponse]


class BatchTaskExtractionResponse(BaseModel):
    message: str
    processed: int
    skipped: int
    failed: int
    tasks_created: int
    results: list[EmailTaskExtractionResponse]
