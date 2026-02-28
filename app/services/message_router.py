"""Inbound message routing layer for WhatsApp webhook payloads."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Literal
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.interfaces.ai_provider import AIProvider
from app.interfaces.messaging_provider import MessagingProvider
from app.models.advisor import Advisor
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.flow_manager import FlowManager
from app.services.intent_engine import IntentEngine

logger = logging.getLogger(__name__)

SenderType = Literal["advisor", "user"]
SenderResolver = Callable[[str, dict[str, Any]], SenderType]


class MessageRouter:
    """Routes inbound webhook payloads using conversation control_mode."""

    def __init__(
        self,
        flow_manager: FlowManager,
        sender_resolver: SenderResolver | None = None,
        *,
        intent_engine: IntentEngine | None = None,
        ai_provider: AIProvider | None = None,
        messaging_provider: MessagingProvider | None = None,
    ) -> None:
        self.flow_manager = flow_manager
        self.sender_resolver = sender_resolver or self._default_sender_resolver
        self.intent_engine = intent_engine
        self.ai_provider = ai_provider
        self.messaging_provider = messaging_provider
        self._last_response_by_user: dict[str, str] = {}

    async def route_message(self, db: Session, incoming_message: dict[str, Any]) -> None:
        """Route one incoming webhook payload to the appropriate processing path."""
        phone = self._extract_sender_phone(incoming_message=incoming_message)
        sender_type = self.sender_resolver(phone, incoming_message)

        if sender_type == "advisor":
            await self._handle_advisor_message(
                db=db,
                phone=phone,
                incoming_message=incoming_message,
            )
            return

        await self._handle_user_message(
            db=db,
            phone=phone,
            incoming_message=incoming_message,
        )

    async def _handle_user_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
    ) -> None:
        if self.intent_engine is None or self.ai_provider is None or self.messaging_provider is None:
            raise RuntimeError(
                "MessageRouter requires intent_engine, ai_provider, and messaging_provider for AI flow handling."
            )

        business_id = self._extract_required_uuid(incoming_message=incoming_message, key="business_id")
        user = self._get_or_create_user(
            db=db,
            business_id=business_id,
            phone=phone,
        )
        conversation = self._get_or_create_active_conversation(
            db=db,
            business_id=business_id,
            user_id=user.id,
        )
        message_text = self._extract_message_text(incoming_message=incoming_message)
        payload = self._build_payload(phone=phone, incoming_message=incoming_message)
        self._persist_message(
            db=db,
            conversation=conversation,
            sender_type="user",
            direction="inbound",
            content=message_text,
            payload=payload,
        )

        if conversation.control_mode == "human":
            return

        intent = self.intent_engine.detect_intent(message=message_text)
        if intent == "human_handoff":
            advisor = self._get_active_advisor(db=db, business_id=conversation.business_id)
            conversation.control_mode = "human"
            conversation.assigned_advisor_id = advisor.id if advisor is not None else None
            db.add(conversation)
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise

            response = "Un asesor continuará la conversación."
            self._persist_message(
                db=db,
                conversation=conversation,
                sender_type="assistant",
                direction="outbound",
                content=response,
                payload={"intent": intent},
            )
            await self.messaging_provider.send_message(user=phone, message=response)
            self._last_response_by_user[phone] = response

            if advisor is not None and advisor.phone.strip():
                client_name, client_phone = self._resolve_client_identity(
                    db=db,
                    conversation=conversation,
                    fallback_phone=phone,
                )
                advisor_message = (
                    "Nueva conversación en modo humano.\n"
                    f"Cliente: {client_name}\n"
                    f"Teléfono: {client_phone}"
                )
                await self.messaging_provider.send_message(user=advisor.phone.strip(), message=advisor_message)
            return

        flow_response = await self.flow_manager.handle(intent=intent, user=phone, message=message_text)
        if flow_response is None:
            context = {
                "user": phone,
                "conversation_id": str(conversation.id),
                "business_id": str(conversation.business_id),
                "user_id": str(conversation.user_id),
                "control_mode": conversation.control_mode,
                "context": conversation.context,
                "intent": intent,
                "mode": self.flow_manager.mode,
            }
            response = await self.ai_provider.generate_response(message=message_text, context=context)
        else:
            response = flow_response

        self._persist_message(
            db=db,
            conversation=conversation,
            sender_type="assistant",
            direction="outbound",
            content=response,
            payload={"intent": intent},
        )
        await self.messaging_provider.send_message(user=phone, message=response)
        self._last_response_by_user[phone] = response

    async def _handle_advisor_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
    ) -> None:
        message_text = self._extract_message_text(incoming_message=incoming_message)
        payload = self._build_payload(phone=phone, incoming_message=incoming_message)
        close_client_phone = self._parse_close_command(message_text=message_text)

        if close_client_phone is not None:
            advisor = self._get_active_advisor_by_phone(db=db, advisor_phone=phone)
            if advisor is None:
                fallback_conversation = self._try_resolve_active_conversation(db=db, incoming_message=incoming_message)
                if fallback_conversation is not None:
                    self._persist_message(
                        db=db,
                        conversation=fallback_conversation,
                        sender_type="advisor",
                        direction="inbound",
                        content=message_text,
                        payload=payload,
                    )
                await self.messaging_provider.send_message(
                    user=phone,
                    message="No se encontró conversación activa con ese cliente.",
                )
                return

            conversation = self._get_active_human_conversation_for_advisor_client(
                db=db,
                advisor=advisor,
                client_phone=close_client_phone,
            )
            if conversation is None:
                fallback_conversation = self._get_active_conversation_for_client_phone(
                    db=db,
                    business_id=advisor.business_id,
                    client_phone=close_client_phone,
                )
                if fallback_conversation is not None:
                    self._persist_message(
                        db=db,
                        conversation=fallback_conversation,
                        sender_type="advisor",
                        direction="inbound",
                        content=message_text,
                        payload=payload,
                    )
                await self.messaging_provider.send_message(
                    user=phone,
                    message="No se encontró conversación activa con ese cliente.",
                )
                return

            self._persist_message(
                db=db,
                conversation=conversation,
                sender_type="advisor",
                direction="inbound",
                content=message_text,
                payload=payload,
            )
            conversation.status = "closed"
            conversation.closed_at = func.now()
            db.add(conversation)
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
            await self.messaging_provider.send_message(user=phone, message="Conversación cerrada correctamente.")
            return

        conversation = self._resolve_active_conversation(db=db, incoming_message=incoming_message)
        self._persist_message(
            db=db,
            conversation=conversation,
            sender_type="advisor",
            direction="inbound",
            content=message_text,
            payload=payload,
        )

    def get_last_response(self, user: str) -> str | None:
        """Return last AI response sent to a user (test/debug helper)."""
        return self._last_response_by_user.get(user)

    def _resolve_active_conversation(self, *, db: Session, incoming_message: dict[str, Any]) -> Conversation:
        business_id_raw = incoming_message.get("business_id")
        user_id_raw = incoming_message.get("user_id")
        if business_id_raw is not None and user_id_raw is not None:
            business_id = self._extract_required_uuid(incoming_message=incoming_message, key="business_id")
            user_id = self._extract_required_uuid(incoming_message=incoming_message, key="user_id")
            return self._get_or_create_active_conversation(
                db=db,
                business_id=business_id,
                user_id=user_id,
            )

        phone = self._extract_sender_phone(incoming_message=incoming_message)
        query = (
            select(Conversation)
            .join(User, Conversation.user_id == User.id)
            .where(
                User.phone == phone,
                Conversation.status == "active",
            )
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )
        conversation = db.execute(query).scalars().first()
        if conversation is None:
            raise ValueError(
                "Incoming message is missing 'business_id'/'user_id' and no active conversation exists for sender phone."
            )
        return conversation

    def _extract_sender_phone(self, *, incoming_message: dict[str, Any]) -> str:
        for key in ("phone", "user", "from", "from_phone", "sender_phone", "wa_id"):
            value = incoming_message.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        raise ValueError("Incoming message is missing sender phone identifier.")

    def _extract_message_text(self, *, incoming_message: dict[str, Any]) -> str:
        for key in ("message", "text", "body"):
            value = incoming_message.get(key)
            if value is not None:
                text = str(value).strip()
                if text:
                    return text
        raise ValueError("Incoming message is missing message content.")

    def _extract_required_uuid(self, *, incoming_message: dict[str, Any], key: str) -> UUID:
        raw_value = incoming_message.get(key)
        if raw_value is None:
            raise ValueError(f"Incoming message is missing required '{key}' value.")
        try:
            return UUID(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Incoming message has invalid UUID for '{key}'.") from exc

    def _get_or_create_active_conversation(
        self,
        db: Session,
        business_id: UUID,
        user_id: UUID,
    ) -> Conversation:
        query = select(Conversation).where(
            Conversation.business_id == business_id,
            Conversation.user_id == user_id,
            Conversation.status == "active",
        )
        conversation = db.execute(query).scalar_one_or_none()
        if conversation is not None:
            return conversation

        conversation = Conversation(
            business_id=business_id,
            user_id=user_id,
            status="active",
            control_mode="ai",
            assigned_advisor_id=None,
            mode=self.flow_manager.mode,
        )
        db.add(conversation)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing_conversation = db.execute(query).scalar_one_or_none()
            if existing_conversation is not None:
                return existing_conversation
            raise
        db.refresh(conversation)
        return conversation

    def _persist_message(
        self,
        db: Session,
        conversation: Conversation,
        sender_type: str,
        direction: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        message = Message(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            sender_type=sender_type,
            direction=direction,
            content=content,
            payload=payload or {},
        )
        conversation.last_message_at = datetime.now(timezone.utc)
        db.add(message)
        db.add(conversation)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    def _build_payload(self, *, phone: str, incoming_message: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {"phone": phone}
        message_id = incoming_message.get("message_id") or incoming_message.get("id")
        if message_id is not None:
            payload["message_id"] = str(message_id)

        timestamp = incoming_message.get("timestamp")
        if timestamp is not None:
            payload["timestamp"] = str(timestamp)

        return payload

    def _default_sender_resolver(self, phone: str, incoming_message: dict[str, Any]) -> SenderType:
        del phone
        sender_type = incoming_message.get("sender_type")
        if isinstance(sender_type, str):
            normalized = sender_type.strip().lower()
            if normalized in {"agent", "advisor"}:
                return "advisor"
            if normalized == "user":
                return "user"

        for flag_name in ("is_agent", "is_advisor", "from_me"):
            flag_value = incoming_message.get(flag_name)
            if isinstance(flag_value, bool):
                return "advisor" if flag_value else "user"

        return "user"

    def _get_active_advisor(self, *, db: Session, business_id: UUID) -> Advisor | None:
        query = (
            select(Advisor)
            .where(
                Advisor.business_id == business_id,
                Advisor.is_active.is_(True),
            )
            .order_by(Advisor.created_at.asc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _get_active_advisor_by_phone(self, *, db: Session, advisor_phone: str) -> Advisor | None:
        query = (
            select(Advisor)
            .where(
                Advisor.phone == advisor_phone,
                Advisor.is_active.is_(True),
            )
            .order_by(Advisor.created_at.asc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _get_active_human_conversation_for_advisor_client(
        self,
        *,
        db: Session,
        advisor: Advisor,
        client_phone: str,
    ) -> Conversation | None:
        query = (
            select(Conversation)
            .join(User, Conversation.user_id == User.id)
            .where(
                Conversation.business_id == advisor.business_id,
                Conversation.status == "active",
                Conversation.control_mode == "human",
                Conversation.assigned_advisor_id == advisor.id,
                User.phone == client_phone,
            )
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _resolve_client_identity(
        self,
        *,
        db: Session,
        conversation: Conversation,
        fallback_phone: str,
    ) -> tuple[str, str]:
        client_name = "Cliente"
        client_phone = fallback_phone

        query = (
            select(User.name, User.phone)
            .where(User.id == conversation.user_id)
            .limit(1)
        )
        row = db.execute(query).first()
        if row is None:
            return client_name, client_phone

        user_name, user_phone = row
        if isinstance(user_name, str) and user_name.strip():
            client_name = user_name.strip()
        if isinstance(user_phone, str) and user_phone.strip():
            client_phone = user_phone.strip()
        return client_name, client_phone

    def _parse_close_command(self, *, message_text: str) -> str | None:
        parts = message_text.strip().split(maxsplit=1)
        if len(parts) != 2:
            return None
        command, raw_phone = parts
        if command.lower() != "/cerrar":
            return None
        normalized_phone = raw_phone.strip()
        if not normalized_phone:
            return None
        return normalized_phone

    def _get_or_create_user(
        self,
        *,
        db: Session,
        business_id: UUID,
        phone: str,
    ) -> User:
        normalized_phone = phone.strip()
        query = select(User).where(
            User.business_id == business_id,
            User.phone == normalized_phone,
        )
        user = db.execute(query).scalars().first()
        if user is not None:
            return user

        user = User(
            business_id=business_id,
            external_id=normalized_phone,
            phone=normalized_phone,
            name=None,
            locale="es",
            is_active=True,
            profile={},
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing_user = db.execute(query).scalars().first()
            if existing_user is not None:
                return existing_user
            raise
        db.refresh(user)
        return user

    def _get_active_conversation_for_client_phone(
        self,
        *,
        db: Session,
        business_id: UUID,
        client_phone: str,
    ) -> Conversation | None:
        query = (
            select(Conversation)
            .join(User, Conversation.user_id == User.id)
            .where(
                Conversation.business_id == business_id,
                Conversation.status == "active",
                User.phone == client_phone,
            )
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _try_resolve_active_conversation(
        self,
        *,
        db: Session,
        incoming_message: dict[str, Any],
    ) -> Conversation | None:
        try:
            return self._resolve_active_conversation(db=db, incoming_message=incoming_message)
        except ValueError:
            return None
