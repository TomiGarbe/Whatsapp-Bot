"""Inbound message routing layer for agent/user and AI/human control paths."""

from __future__ import annotations

import logging
from typing import Any, Callable, Literal, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.interfaces.ai_provider import AIProvider
from app.interfaces.messaging_provider import MessagingProvider
from app.models.conversation import Conversation
from app.services.flow_manager import FlowManager
from app.services.intent_engine import IntentEngine

logger = logging.getLogger(__name__)

SenderType = Literal["agent", "user"]
SenderResolver = Callable[[str, dict[str, Any]], SenderType]


class HumanSupportServiceProtocol(Protocol):
    """Contract for human-support handoff behavior."""

    async def handle_agent_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
    ) -> None:
        """Handle inbound messages coming from an agent."""

    async def handle_user_human_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
        conversation: Conversation,
    ) -> None:
        """Handle user messages when conversation is under human control."""


class StubHumanSupportService:
    """Temporary human-support implementation until real logic is added."""

    async def handle_agent_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
    ) -> None:
        logger.info("Agent message received for %s. Human support workflow pending.", phone)
        del db
        del incoming_message

    async def handle_user_human_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
        conversation: Conversation,
    ) -> None:
        logger.info(
            "User message received in human mode for %s. Human support workflow pending.",
            phone,
        )
        del db
        del incoming_message
        del conversation


class MessageRouter:
    """Routes inbound webhook messages to the correct handling flow."""

    def __init__(
        self,
        flow_manager: FlowManager,
        human_support_service: HumanSupportServiceProtocol | None = None,
        sender_resolver: SenderResolver | None = None,
        *,
        intent_engine: IntentEngine | None = None,
        ai_provider: AIProvider | None = None,
        messaging_provider: MessagingProvider | None = None,
    ) -> None:
        self.flow_manager = flow_manager
        self.human_support_service = human_support_service or StubHumanSupportService()
        self.sender_resolver = sender_resolver or self._default_sender_resolver
        self.intent_engine = intent_engine
        self.ai_provider = ai_provider
        self.messaging_provider = messaging_provider
        self._last_response_by_user: dict[str, str] = {}

    async def route_message(self, db: Session, incoming_message: dict[str, Any]) -> None:
        """Route one incoming webhook payload to the appropriate processing path."""
        phone = self._extract_sender_phone(incoming_message=incoming_message)
        sender_type = self.sender_resolver(phone, incoming_message)

        if sender_type == "agent":
            await self._handle_agent_message(
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
        business_id = self._extract_required_uuid(incoming_message=incoming_message, key="business_id")
        user_id = self._extract_required_uuid(incoming_message=incoming_message, key="user_id")
        conversation = self._get_or_create_active_conversation(
            db=db,
            business_id=business_id,
            user_id=user_id,
        )

        if conversation.control_mode == "human":
            await self.human_support_service.handle_user_human_message(
                db=db,
                phone=phone,
                incoming_message=incoming_message,
                conversation=conversation,
            )
            return

        await self._continue_ai_flow(
            phone=phone,
            incoming_message=incoming_message,
            conversation=conversation,
        )

    async def _handle_agent_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
    ) -> None:
        await self.human_support_service.handle_agent_message(
            db=db,
            phone=phone,
            incoming_message=incoming_message,
        )

    async def _continue_ai_flow(
        self,
        *,
        phone: str,
        incoming_message: dict[str, Any],
        conversation: Conversation,
    ) -> None:
        if self.intent_engine is None or self.ai_provider is None or self.messaging_provider is None:
            raise RuntimeError(
                "MessageRouter requires intent_engine, ai_provider, and messaging_provider for AI flow handling."
            )

        message_text = self._extract_message_text(incoming_message=incoming_message)
        intent = self.intent_engine.detect_intent(message=message_text)
        flow_response = await self.flow_manager.handle(intent=intent, user=phone, message=message_text)

        if flow_response is None:
            context = {
                "user": phone,
                "conversation_id": str(conversation.id),
                "business_id": str(conversation.business_id),
                "user_id": str(conversation.user_id),
                "control_mode": conversation.control_mode,
                "human_status": conversation.human_status,
                "context": conversation.context,
                "intent": intent,
                "mode": self.flow_manager.mode,
            }
            response = await self.ai_provider.generate_response(message=message_text, context=context)
        else:
            response = flow_response

        await self.messaging_provider.send_message(user=phone, message=response)
        self._last_response_by_user[phone] = response

    def get_last_response(self, user: str) -> str | None:
        """Return last AI response sent to a user (test/debug helper)."""
        return self._last_response_by_user.get(user)

    def _extract_sender_phone(self, *, incoming_message: dict[str, Any]) -> str:
        for key in ("phone", "user", "from", "from_phone", "sender_phone"):
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
            human_status=None,
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

    def _default_sender_resolver(self, phone: str, incoming_message: dict[str, Any]) -> SenderType:
        del phone
        sender_type = incoming_message.get("sender_type")
        if isinstance(sender_type, str):
            normalized = sender_type.strip().lower()
            if normalized in {"agent", "user"}:
                return normalized

        is_agent_flag = incoming_message.get("is_agent")
        if isinstance(is_agent_flag, bool):
            return "agent" if is_agent_flag else "user"

        return "user"
