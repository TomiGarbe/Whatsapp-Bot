"""Conversation model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, TIMESTAMP, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.advisor import Advisor
    from app.models.business import Business
    from app.models.message import Message
    from app.models.request import Request
    from app.models.user import User


class Conversation(Base):
    """Conversation session for a user and business."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status in ('active', 'closed')", name="ck_conversations_status"),
        CheckConstraint("mode in ('assisted', 'autonomous')", name="ck_conversations_mode"),
        CheckConstraint("control_mode in ('ai', 'human')", name="ck_conversations_control_mode"),
        Index("ix_conversations_business_id", "business_id"),
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_assigned_advisor_id", "assigned_advisor_id"),
        Index("ix_conversations_last_message_at", "last_message_at"),
        Index(
            "uq_conversations_active_user",
            "business_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("advisors.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="whatsapp")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="assisted")
    control_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_message_at: Mapped[Any | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_at: Mapped[Any | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="conversations")
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    assigned_advisor: Mapped["Advisor | None"] = relationship("Advisor", back_populates="assigned_conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    requests: Mapped[list["Request"]] = relationship("Request", back_populates="conversation")
