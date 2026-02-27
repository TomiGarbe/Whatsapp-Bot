"""Advisor model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.conversation import Conversation


class Advisor(Base):
    """Human advisor contact used for human-handoff notifications."""

    __tablename__ = "advisors"
    __table_args__ = (
        Index("ix_advisors_business_id", "business_id"),
        Index("ix_advisors_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    business: Mapped["Business"] = relationship("Business", back_populates="advisors")
    assigned_conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="assigned_advisor",
    )
