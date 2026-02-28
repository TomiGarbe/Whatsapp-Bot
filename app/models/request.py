"""Request model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.conversation import Conversation
    from app.models.item import Item
    from app.models.user import User


class Request(Base):
    """Generic user request (booking/order/appointment/meeting)."""

    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'confirmed', 'cancelled', 'completed', 'rejected')",
            name="ck_requests_status",
        ),
        CheckConstraint("char_length(type) > 0", name="ck_requests_type_not_empty"),
        Index("ix_requests_business_id", "business_id"),
        Index("ix_requests_user_id", "user_id"),
        Index("ix_requests_status", "status"),
        Index("ix_requests_scheduled_for", "scheduled_for"),
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
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False, default="generic")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    scheduled_for: Mapped[Any | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    human_validation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    request_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    validated_at: Mapped[Any | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="requests")
    user: Mapped["User"] = relationship("User", back_populates="requests")
    conversation: Mapped["Conversation | None"] = relationship("Conversation", back_populates="requests")
    item: Mapped["Item | None"] = relationship("Item", back_populates="requests")

