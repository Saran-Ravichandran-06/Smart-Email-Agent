from pydantic import BaseModel, Field

from app.ai.reply_generation import REPLY_TONES


class ReplyDraftRequest(BaseModel):
    tone: str = Field(
        default="neutral",
        description=f"Reply tone: {', '.join(REPLY_TONES)}",
    )
    previous_draft: str | None = Field(
        default=None,
        description="Optional prior draft to avoid repetitive regeneration output.",
    )


class ReplyDraftResponse(BaseModel):
    email_id: int
    thread_id: str
    tone: str
    draft: str
    context_messages_used: int
    regenerated: bool
    message: str


class ReplySendRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=20000)


class ReplySendResponse(BaseModel):
    email_id: int
    gmail_message_id: str
    thread_id: str
    sent_at: str
    message: str
