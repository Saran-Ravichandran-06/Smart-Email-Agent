from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    gmail_history_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    label_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_cleaned: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    task_extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followup_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gmail_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gmail_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_sent_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_sent_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_sent_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="emails")
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="email",
        cascade="all, delete-orphan",
    )
