from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.email import Email
    from app.models.user import User


class FollowUp(Base):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    needs_followup: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="open")
    draft_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_email_id: Mapped[int | None] = mapped_column(
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
    )
    priority_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="followups")
    latest_email: Mapped["Email | None"] = relationship("Email", foreign_keys=[latest_email_id])
