"""Agent model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.conversation import Conversation, ConversationTransfer
    from app.models.message import Message
    from app.models.request import Request


class Agent(Base):
    """Human agent for assisted support and validation."""

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("business_id", "email", name="uq_agents_business_email"),
        CheckConstraint("role in ('agent', 'admin', 'supervisor')", name="ck_agents_role"),
        Index("ix_agents_business_id", "business_id"),
        Index("ix_agents_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="agent")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="agents")
    assigned_conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="assigned_agent",
    )
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="agent")
    validated_requests: Mapped[list["Request"]] = relationship("Request", back_populates="validated_by_agent")
    outgoing_transfers: Mapped[list["ConversationTransfer"]] = relationship(
        "ConversationTransfer",
        back_populates="from_agent",
        foreign_keys="ConversationTransfer.from_agent_id",
    )
    incoming_transfers: Mapped[list["ConversationTransfer"]] = relationship(
        "ConversationTransfer",
        back_populates="to_agent",
        foreign_keys="ConversationTransfer.to_agent_id",
    )

