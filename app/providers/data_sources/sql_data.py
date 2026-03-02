"""SQLAlchemy-backed data source implementation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.interfaces.data_source import DataSource
from app.models.conversation import Conversation
from app.models.item import Item
from app.models.request import Request
from app.models.user import User


class SQLDataSource(DataSource):
    """Tenant-scoped data source that reads and writes on PostgreSQL."""

    def __init__(self, db: Session, business_id: UUID) -> None:
        self.db = db
        self.business_id = business_id

    async def get_items(self) -> list[dict[str, Any]]:
        query = (
            select(Item)
            .where(
                Item.business_id == self.business_id,
                Item.is_active.is_(True),
            )
            .order_by(Item.name.asc())
        )
        items = self.db.execute(query).scalars().all()
        return [self._serialize_item(item) for item in items]

    async def get_item_by_id(self, item_id: str) -> dict[str, Any] | None:
        item_uuid = self._parse_uuid(item_id)
        if item_uuid is None:
            return None

        query = select(Item).where(
            Item.id == item_uuid,
            Item.business_id == self.business_id,
            Item.is_active.is_(True),
        )
        item = self.db.execute(query).scalars().first()
        if item is None:
            return None
        return self._serialize_item(item)

    async def check_availability(self, item_id: str, datetime: str | None = None) -> bool:
        del datetime
        item = await self.get_item_by_id(item_id=item_id)
        return item is not None

    async def create_request(self, user: str, data: dict[str, Any]) -> dict[str, Any]:
        normalized_phone = user.strip()
        if not normalized_phone:
            raise ValueError("User phone cannot be empty when creating a request.")

        user_record = self._find_user_by_phone(phone=normalized_phone)
        if user_record is None:
            user_record = User(
                business_id=self.business_id,
                external_id=normalized_phone,
                phone=normalized_phone,
                name=None,
                locale="es",
                is_active=True,
                profile={},
            )
            self.db.add(user_record)
            try:
                self.db.flush()
            except IntegrityError:
                self.db.rollback()
                user_record = self._find_user_by_phone(phone=normalized_phone)
                if user_record is None:
                    raise

        request = Request(
            business_id=self.business_id,
            user_id=user_record.id,
            conversation_id=self._resolve_conversation_id(data.get("conversation_id")),
            item_id=self._resolve_item_id(data.get("item_id")),
            type=self._resolve_request_type(data=data),
            status="pending",
            human_validation_required=bool(data.get("human_validation_required", True)),
            request_data=dict(data),
        )
        self.db.add(request)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(request)
        return self._serialize_request(request)

    async def confirm_request(self, request_id: str) -> dict[str, Any]:
        request_uuid = self._parse_uuid(request_id)
        if request_uuid is None:
            raise ValueError("Request id is invalid.")

        query = select(Request).where(
            Request.id == request_uuid,
            Request.business_id == self.business_id,
        )
        request = self.db.execute(query).scalars().first()
        if request is None:
            raise ValueError(f"Request '{request_id}' not found.")

        request.status = "confirmed"
        self.db.add(request)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(request)
        return self._serialize_request(request)

    def _find_user_by_phone(self, *, phone: str) -> User | None:
        query = select(User).where(
            User.business_id == self.business_id,
            User.phone == phone,
        )
        return self.db.execute(query).scalars().first()

    def _resolve_conversation_id(self, raw_value: Any) -> UUID | None:
        conversation_id = self._parse_uuid(raw_value)
        if conversation_id is None:
            return None

        query = select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.business_id == self.business_id,
        )
        existing_id = self.db.execute(query).scalars().first()
        return existing_id

    def _resolve_item_id(self, raw_value: Any) -> UUID | None:
        item_id = self._parse_uuid(raw_value)
        if item_id is None:
            return None

        query = select(Item.id).where(
            Item.id == item_id,
            Item.business_id == self.business_id,
            Item.is_active.is_(True),
        )
        existing_id = self.db.execute(query).scalars().first()
        return existing_id

    def _resolve_request_type(self, *, data: dict[str, Any]) -> str:
        raw_type = data.get("type")
        if raw_type is None:
            return "generic"
        normalized = str(raw_type).strip().lower()
        return normalized or "generic"

    def _serialize_item(self, item: Item) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "price": self._decimal_to_float(item.price),
            "currency": item.currency,
            "type": item.type,
            "is_active": item.is_active,
            "item_data": item.item_data,
        }

    def _serialize_request(self, request: Request) -> dict[str, Any]:
        return {
            "id": str(request.id),
            "business_id": str(request.business_id),
            "user_id": str(request.user_id),
            "conversation_id": str(request.conversation_id) if request.conversation_id is not None else None,
            "item_id": str(request.item_id) if request.item_id is not None else None,
            "type": request.type,
            "status": request.status,
            "human_validation_required": request.human_validation_required,
            "request_data": request.request_data,
        }

    def _parse_uuid(self, raw_value: Any) -> UUID | None:
        if raw_value is None:
            return None
        try:
            return UUID(str(raw_value))
        except (TypeError, ValueError):
            return None

    def _decimal_to_float(self, value: Decimal | None) -> float:
        if value is None:
            return 0.0
        return float(value)
