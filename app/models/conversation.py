"""Conversation and conversation transfer models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, TIMESTAMP, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.business import Business
    from app.models.message import Message
    from app.models.request import Request
    from app.models.user import User


class Conversation(Base):
    """Conversation session for a user and business."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status in ('active', 'closed', 'archived')", name="ck_conversations_status"),
        CheckConstraint("mode in ('assisted', 'autonomous')", name="ck_conversations_mode"),
        CheckConstraint("control_mode in ('ai', 'human')", name="ck_conversations_control_mode"),
        Index("ix_conversations_business_id", "business_id"),
        Index("ix_conversations_user_id", "user_id"),
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
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
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
    assigned_agent: Mapped["Agent | None"] = relationship("Agent", back_populates="assigned_conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    requests: Mapped[list["Request"]] = relationship("Request", back_populates="conversation")
    transfers: Mapped[list["ConversationTransfer"]] = relationship(
        "ConversationTransfer",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationTransfer(Base):
    """Tracks transfers of a conversation between agents."""

    __tablename__ = "conversation_transfers"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'accepted', 'rejected', 'cancelled')",
            name="ck_conversation_transfers_status",
        ),
        CheckConstraint(
            "from_mode in ('ai', 'human')",
            name="ck_conversation_transfers_from_mode",
        ),
        CheckConstraint(
            "to_mode in ('ai', 'human')",
            name="ck_conversation_transfers_to_mode",
        ),
        Index("ix_conversation_transfers_conversation_id", "conversation_id"),
        Index("ix_conversation_transfers_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    from_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    to_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    transfer_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    requested_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[Any | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="transfers")
    from_agent: Mapped["Agent | None"] = relationship(
        "Agent",
        back_populates="outgoing_transfers",
        foreign_keys=[from_agent_id],
    )
    to_agent: Mapped["Agent | None"] = relationship(
        "Agent",
        back_populates="incoming_transfers",
        foreign_keys=[to_agent_id],
    )
