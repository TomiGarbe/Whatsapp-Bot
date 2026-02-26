"""Business and business configuration models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.conversation import Conversation
    from app.models.item import Item
    from app.models.plan import Plan
    from app.models.request import Request
    from app.models.usage import BusinessUsage
    from app.models.user import User


class Business(Base):
    """Tenant/business configuration root."""

    __tablename__ = "businesses"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_businesses_slug"),
        CheckConstraint("status in ('active', 'inactive', 'suspended')", name="ck_businesses_status"),
        Index("ix_businesses_plan_id", "plan_id"),
        Index("ix_businesses_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(80), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    whatsapp_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    plan: Mapped["Plan"] = relationship("Plan", back_populates="businesses")
    config: Mapped["BusinessConfig | None"] = relationship(
        "BusinessConfig",
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="business", cascade="all, delete-orphan")
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="business", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    items: Mapped[list["Item"]] = relationship("Item", back_populates="business", cascade="all, delete-orphan")
    requests: Mapped[list["Request"]] = relationship("Request", back_populates="business", cascade="all, delete-orphan")
    usages: Mapped[list["BusinessUsage"]] = relationship(
        "BusinessUsage",
        back_populates="business",
        cascade="all, delete-orphan",
    )


class BusinessConfig(Base):
    """Operational config for each business."""

    __tablename__ = "business_configs"
    __table_args__ = (
        UniqueConstraint("business_id", name="uq_business_configs_business_id"),
        CheckConstraint("mode in ('assisted', 'autonomous')", name="ck_business_configs_mode"),
        Index("ix_business_configs_mode", "mode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="assisted")
    handoff_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assisted_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    autonomous_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="config")

