"""Usage tracking models."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.user import User


class BusinessUsage(Base):
    """Usage metrics aggregated at business level."""

    __tablename__ = "business_usages"
    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "period_start",
            "period_end",
            "metric",
            name="uq_business_usages_period_metric",
        ),
        CheckConstraint("used_count >= 0", name="ck_business_usages_used_count_non_negative"),
        CheckConstraint("limit_count is null or limit_count >= 0", name="ck_business_usages_limit_count_non_negative"),
        CheckConstraint("period_end >= period_start", name="ck_business_usages_period_order"),
        Index("ix_business_usages_business_id", "business_id"),
        Index("ix_business_usages_metric", "metric"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(String(40), nullable=False, default="messages")
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="usages")


class UserUsage(Base):
    """Usage metrics aggregated at user level."""

    __tablename__ = "user_usages"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "period_start",
            "period_end",
            "metric",
            name="uq_user_usages_period_metric",
        ),
        CheckConstraint("used_count >= 0", name="ck_user_usages_used_count_non_negative"),
        CheckConstraint("limit_count is null or limit_count >= 0", name="ck_user_usages_limit_count_non_negative"),
        CheckConstraint("period_end >= period_start", name="ck_user_usages_period_order"),
        Index("ix_user_usages_user_id", "user_id"),
        Index("ix_user_usages_metric", "metric"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(String(40), nullable=False, default="messages")
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="usages")

