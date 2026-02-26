"""Bot service entrypoint that delegates routing to MessageRouter."""

from __future__ import annotations

from typing import Any

from app.interfaces.ai_provider import AIProvider
from app.interfaces.messaging_provider import MessagingProvider
from sqlalchemy.orm import Session

from app.services.flow_manager import FlowManager
from app.services.human_support_service import HumanSupportService
from app.services.intent_engine import IntentEngine
from app.services.message_router import HumanSupportServiceProtocol, MessageRouter, SenderResolver


class BotService:
    """Thin facade that forwards webhook payloads to MessageRouter."""

    def __init__(
        self,
        ai_provider: AIProvider,
        messaging_provider: MessagingProvider,
        intent_engine: IntentEngine,
        flow_manager: FlowManager,
        human_support_service: HumanSupportServiceProtocol | None = None,
        sender_resolver: SenderResolver | None = None,
    ) -> None:
        resolved_human_support_service = human_support_service or HumanSupportService(
            messaging_provider=messaging_provider
        )
        self.message_router = MessageRouter(
            flow_manager=flow_manager,
            human_support_service=resolved_human_support_service,
            sender_resolver=sender_resolver,
            intent_engine=intent_engine,
            ai_provider=ai_provider,
            messaging_provider=messaging_provider,
        )

    async def handle_webhook(self, db: Session, incoming_message: dict[str, Any]) -> None:
        """Receive webhook payload and route it through MessageRouter."""
        await self.message_router.route_message(db=db, incoming_message=incoming_message)

    async def handle_message(
        self,
        db: Session,
        *,
        business_id: str,
        user_id: str,
        user: str,
        message: str,
    ) -> dict[str, str]:
        """Compatibility adapter for existing test endpoint payload format."""
        incoming_message = {
            "business_id": business_id,
            "user_id": user_id,
            "user": user,
            "message": message,
            "sender_type": "user",
        }
        await self.handle_webhook(db=db, incoming_message=incoming_message)
        response = self.message_router.get_last_response(user=user) or ""
        return {"user": user, "response": response}

