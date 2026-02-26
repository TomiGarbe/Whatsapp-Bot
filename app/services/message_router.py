"""Inbound message routing layer for agent/user and AI/human control paths."""

from __future__ import annotations

import logging
from typing import Any, Callable, Literal, Protocol

from app.interfaces.ai_provider import AIProvider
from app.interfaces.messaging_provider import MessagingProvider
from app.services.conversation_manager import ConversationContext, ConversationManager
from app.services.flow_manager import FlowManager
from app.services.intent_engine import IntentEngine

logger = logging.getLogger(__name__)

SenderType = Literal["agent", "user"]
SenderResolver = Callable[[str, dict[str, Any]], SenderType]


class HumanSupportServiceProtocol(Protocol):
    """Contract for human-support handoff behavior."""

    async def handle_agent_message(self, *, phone: str, incoming_message: dict[str, Any]) -> None:
        """Handle inbound messages coming from an agent."""

    async def handle_user_human_message(
        self,
        *,
        phone: str,
        incoming_message: dict[str, Any],
        conversation: ConversationContext,
    ) -> None:
        """Handle user messages when conversation is under human control."""


class StubHumanSupportService:
    """Temporary human-support implementation until real logic is added."""

    async def handle_agent_message(self, *, phone: str, incoming_message: dict[str, Any]) -> None:
        logger.info("Agent message received for %s. Human support workflow pending.", phone)
        del incoming_message

    async def handle_user_human_message(
        self,
        *,
        phone: str,
        incoming_message: dict[str, Any],
        conversation: ConversationContext,
    ) -> None:
        logger.info(
            "User message received in human mode for %s. Human support workflow pending.",
            phone,
        )
        del incoming_message
        del conversation


class MessageRouter:
    """Routes inbound webhook messages to the correct handling flow."""

    def __init__(
        self,
        conversation_manager: ConversationManager,
        flow_manager: FlowManager,
        human_support_service: HumanSupportServiceProtocol | None = None,
        sender_resolver: SenderResolver | None = None,
        *,
        intent_engine: IntentEngine | None = None,
        ai_provider: AIProvider | None = None,
        messaging_provider: MessagingProvider | None = None,
    ) -> None:
        self.conversation_manager = conversation_manager
        self.flow_manager = flow_manager
        self.human_support_service = human_support_service or StubHumanSupportService()
        self.sender_resolver = sender_resolver or self._default_sender_resolver
        self.intent_engine = intent_engine
        self.ai_provider = ai_provider
        self.messaging_provider = messaging_provider
        self._last_response_by_user: dict[str, str] = {}

    async def route_message(self, incoming_message: dict[str, Any]) -> None:
        """Route one incoming webhook payload to the appropriate processing path."""
        phone = self._extract_sender_phone(incoming_message=incoming_message)
        sender_type = self.sender_resolver(phone, incoming_message)

        if sender_type == "agent":
            await self._handle_agent_message(phone=phone, incoming_message=incoming_message)
            return

        await self._handle_user_message(phone=phone, incoming_message=incoming_message)

    async def _handle_user_message(self, *, phone: str, incoming_message: dict[str, Any]) -> None:
        conversation = self.conversation_manager.get_or_create_active_conversation(user=phone)

        if conversation.control_mode == "human":
            await self.human_support_service.handle_user_human_message(
                phone=phone,
                incoming_message=incoming_message,
                conversation=conversation,
            )
            return

        await self._continue_ai_flow(phone=phone, incoming_message=incoming_message, conversation=conversation)

    async def _handle_agent_message(self, *, phone: str, incoming_message: dict[str, Any]) -> None:
        await self.human_support_service.handle_agent_message(phone=phone, incoming_message=incoming_message)

    async def _continue_ai_flow(
        self,
        *,
        phone: str,
        incoming_message: dict[str, Any],
        conversation: ConversationContext,
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
                "state": conversation.state,
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
