from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.email import Email
    from app.models.followup import FollowUp
    from app.models.oauth_token import OAuthToken


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    emails: Mapped[list["Email"]] = relationship(
        "Email",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    oauth_token: Mapped["OAuthToken | None"] = relationship(
        "OAuthToken",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    followups: Mapped[list["FollowUp"]] = relationship(
        "FollowUp",
        back_populates="user",
        cascade="all, delete-orphan",
    )
