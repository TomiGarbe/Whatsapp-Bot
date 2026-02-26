"""Plan model."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Index, Integer, Numeric, String, TIMESTAMP, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business import Business


class Plan(Base):
    """Subscription plan for businesses."""

    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("name", name="uq_plans_name"),
        UniqueConstraint("code", name="uq_plans_code"),
        CheckConstraint("price_monthly >= 0", name="ck_plans_price_monthly_non_negative"),
        CheckConstraint("message_quota >= 0", name="ck_plans_message_quota_non_negative"),
        Index("ix_plans_code", "code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    message_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    businesses: Mapped[list["Business"]] = relationship("Business", back_populates="plan")

