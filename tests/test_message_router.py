"""Unit tests for MVP MessageRouter behavior."""

from __future__ import annotations

import unittest
from typing import Any
from uuid import UUID, uuid4

from app.models.advisor import Advisor
from app.models.conversation import Conversation
from app.services.intent_engine import IntentEngine
from app.services.message_router import MessageRouter


class StubFlowManager:
    """Flow manager stub with configurable per-intent responses."""

    mode = "assisted"

    def __init__(self, responses: dict[str, str | None] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[dict[str, str]] = []

    async def handle(self, intent: str, user: str, message: str) -> str | None:
        self.calls.append({"intent": intent, "user": user, "message": message})
        return self.responses.get(intent)


class StubAIProvider:
    """AI provider test double that records calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def generate_response(self, message: str, context: dict[str, Any]) -> str:
        self.calls.append({"message": message, "context": context})
        return "[AI FALLBACK]"


class StubMessagingProvider:
    """Messaging provider test double that records outbound sends."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, str]] = []

    async def send_message(self, user: str, message: str) -> None:
        self.sent_messages.append({"user": user, "message": message})


class StubSession:
    """Minimal Session-like object used by router tests."""

    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0
        self.added_objects: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added_objects.append(obj)

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class RecordingMessageRouter(MessageRouter):
    """MessageRouter that bypasses DB queries and records persisted messages."""

    def __init__(
        self,
        *,
        flow_manager: StubFlowManager,
        conversation: Conversation,
        intent_engine: IntentEngine,
        ai_provider: StubAIProvider,
        messaging_provider: StubMessagingProvider,
    ) -> None:
        super().__init__(
            flow_manager=flow_manager,
            intent_engine=intent_engine,
            ai_provider=ai_provider,
            messaging_provider=messaging_provider,
        )
        self.conversation = conversation
        self.persisted_messages: list[dict[str, Any]] = []
        self.active_advisor_for_business: Advisor | None = None
        self.active_advisor_by_phone: Advisor | None = None
        self.client_identity: tuple[str, str] = ("Cliente", "+5490000000000")
        self.command_conversation: Conversation | None = None
        self.fallback_command_conversation: Conversation | None = None

    def _get_or_create_active_conversation(
        self,
        db: StubSession,
        business_id: UUID,
        user_id: UUID,
    ) -> Conversation:
        del db
        self.conversation.business_id = business_id
        self.conversation.user_id = user_id
        return self.conversation

    def _persist_message(
        self,
        db: StubSession,
        conversation: Conversation,
        sender_type: str,
        direction: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        del db
        self.persisted_messages.append(
            {
                "conversation_id": conversation.id,
                "sender_type": sender_type,
                "direction": direction,
                "content": content,
                "payload": payload or {},
            }
        )

    def _get_active_advisor(self, *, db: StubSession, business_id: UUID) -> Advisor | None:
        del db
        del business_id
        return self.active_advisor_for_business

    def _get_active_advisor_by_phone(self, *, db: StubSession, advisor_phone: str) -> Advisor | None:
        del db
        del advisor_phone
        return self.active_advisor_by_phone

    def _get_active_human_conversation_for_advisor_client(
        self,
        *,
        db: StubSession,
        advisor: Advisor,
        client_phone: str,
    ) -> Conversation | None:
        del db
        del advisor
        del client_phone
        return self.command_conversation

    def _get_active_conversation_for_client_phone(
        self,
        *,
        db: StubSession,
        business_id: UUID,
        client_phone: str,
    ) -> Conversation | None:
        del db
        del business_id
        del client_phone
        return self.fallback_command_conversation

    def _try_resolve_active_conversation(
        self,
        *,
        db: StubSession,
        incoming_message: dict[str, Any],
    ) -> Conversation | None:
        del db
        del incoming_message
        return self.fallback_command_conversation

    def _resolve_client_identity(
        self,
        *,
        db: StubSession,
        conversation: Conversation,
        fallback_phone: str,
    ) -> tuple[str, str]:
        del db
        del conversation
        del fallback_phone
        return self.client_identity


class MessageRouterTestCase(unittest.IsolatedAsyncioTestCase):
    """Covers user AI path, handoff, advisor storage, and manual close command."""

    def _build_router(self, *, flow_responses: dict[str, str | None] | None = None) -> tuple[
        RecordingMessageRouter,
        StubSession,
        StubFlowManager,
        StubAIProvider,
        StubMessagingProvider,
        UUID,
        UUID,
        str,
    ]:
        business_id = uuid4()
        user_id = uuid4()
        phone = "+5491122334455"
        conversation = Conversation(
            business_id=business_id,
            user_id=user_id,
            mode="assisted",
            status="active",
            control_mode="ai",
            assigned_advisor_id=None,
        )
        db = StubSession()
        flow_manager = StubFlowManager(responses=flow_responses)
        ai_provider = StubAIProvider()
        messaging_provider = StubMessagingProvider()
        router = RecordingMessageRouter(
            flow_manager=flow_manager,
            conversation=conversation,
            intent_engine=IntentEngine(),
            ai_provider=ai_provider,
            messaging_provider=messaging_provider,
        )
        return router, db, flow_manager, ai_provider, messaging_provider, business_id, user_id, phone

    async def test_user_normal_ai_path(self) -> None:
        router, db, flow_manager, ai_provider, messaging_provider, business_id, user_id, phone = self._build_router(
            flow_responses={"greeting": "Hola, soy el bot."}
        )
        await router.route_message(
            db=db,
            incoming_message={
                "business_id": str(business_id),
                "user_id": str(user_id),
                "phone": phone,
                "message": "hola",
                "message_id": "wamid.001",
                "timestamp": "1700000000",
            },
        )

        self.assertEqual(len(router.persisted_messages), 2)
        self.assertEqual(router.persisted_messages[0]["sender_type"], "user")
        self.assertEqual(router.persisted_messages[1]["sender_type"], "assistant")
        self.assertEqual(router.get_last_response(phone), "Hola, soy el bot.")
        self.assertEqual(len(flow_manager.calls), 1)
        self.assertEqual(len(ai_provider.calls), 0)
        self.assertEqual(messaging_provider.sent_messages, [{"user": phone, "message": "Hola, soy el bot."}])

    async def test_user_handoff_assigns_advisor_and_notifies(self) -> None:
        router, db, flow_manager, ai_provider, messaging_provider, business_id, user_id, phone = self._build_router()
        advisor_id = uuid4()
        advisor_phone = "+5491166677788"
        router.active_advisor_for_business = Advisor(
            id=advisor_id,
            business_id=business_id,
            name="Ana",
            phone=advisor_phone,
            is_active=True,
        )
        router.client_identity = ("Carlos Perez", "+5491122233344")

        await router.route_message(
            db=db,
            incoming_message={
                "business_id": str(business_id),
                "user_id": str(user_id),
                "phone": phone,
                "message": "quiero hablar con un asesor humano",
                "message_id": "wamid.002",
                "timestamp": "1700000001",
            },
        )

        self.assertEqual(router.conversation.control_mode, "human")
        self.assertEqual(router.conversation.assigned_advisor_id, advisor_id)
        self.assertEqual(db.commit_calls, 1)
        self.assertEqual(len(router.persisted_messages), 2)
        self.assertEqual(router.persisted_messages[0]["sender_type"], "user")
        self.assertEqual(router.persisted_messages[1]["sender_type"], "assistant")
        self.assertEqual(len(flow_manager.calls), 0)
        self.assertEqual(len(ai_provider.calls), 0)
        self.assertEqual(len(messaging_provider.sent_messages), 2)
        self.assertEqual(messaging_provider.sent_messages[0]["user"], phone)
        self.assertEqual(messaging_provider.sent_messages[1]["user"], advisor_phone)
        self.assertIn("Cliente: Carlos Perez", messaging_provider.sent_messages[1]["message"])
        self.assertIn("Teléfono: +5491122233344", messaging_provider.sent_messages[1]["message"])

    async def test_advisor_message_path_stores_without_ai(self) -> None:
        router, db, flow_manager, ai_provider, messaging_provider, business_id, user_id, phone = self._build_router()
        router.conversation.control_mode = "human"

        await router.route_message(
            db=db,
            incoming_message={
                "business_id": str(business_id),
                "user_id": str(user_id),
                "phone": phone,
                "message": "Soy el asesor, te ayudo con esto.",
                "sender_type": "advisor",
                "message_id": "wamid.004",
                "timestamp": "1700000003",
            },
        )

        self.assertEqual(len(router.persisted_messages), 1)
        self.assertEqual(router.persisted_messages[0]["sender_type"], "advisor")
        self.assertEqual(router.persisted_messages[0]["direction"], "inbound")
        self.assertEqual(router.persisted_messages[0]["payload"]["message_id"], "wamid.004")
        self.assertEqual(router.persisted_messages[0]["payload"]["timestamp"], "1700000003")
        self.assertEqual(len(flow_manager.calls), 0)
        self.assertEqual(len(ai_provider.calls), 0)
        self.assertEqual(messaging_provider.sent_messages, [])

    async def test_advisor_close_command_closes_assigned_conversation(self) -> None:
        router, db, flow_manager, ai_provider, messaging_provider, business_id, user_id, _ = self._build_router()
        advisor_id = uuid4()
        advisor_phone = "+5491100000000"
        client_phone = "+5491199999999"
        advisor = Advisor(
            id=advisor_id,
            business_id=business_id,
            name="Ana",
            phone=advisor_phone,
            is_active=True,
        )
        router.active_advisor_by_phone = advisor
        router.conversation.control_mode = "human"
        router.conversation.status = "active"
        router.conversation.assigned_advisor_id = advisor_id
        router.command_conversation = router.conversation

        await router.route_message(
            db=db,
            incoming_message={
                "phone": advisor_phone,
                "sender_type": "advisor",
                "message": f"/cerrar {client_phone}",
                "message_id": "wamid.010",
                "timestamp": "1700000010",
            },
        )

        self.assertEqual(len(router.persisted_messages), 1)
        self.assertEqual(router.persisted_messages[0]["sender_type"], "advisor")
        self.assertEqual(router.conversation.status, "closed")
        self.assertEqual(router.conversation.control_mode, "ai")
        self.assertIsNone(router.conversation.assigned_advisor_id)
        self.assertEqual(db.commit_calls, 1)
        self.assertEqual(len(flow_manager.calls), 0)
        self.assertEqual(len(ai_provider.calls), 0)
        self.assertEqual(
            messaging_provider.sent_messages,
            [{"user": advisor_phone, "message": "Conversación cerrada correctamente."}],
        )

    async def test_advisor_close_command_not_found(self) -> None:
        router, db, flow_manager, ai_provider, messaging_provider, _, _, _ = self._build_router()
        advisor_phone = "+5491100000000"
        router.active_advisor_by_phone = Advisor(
            id=uuid4(),
            business_id=uuid4(),
            name="Ana",
            phone=advisor_phone,
            is_active=True,
        )
        router.command_conversation = None

        await router.route_message(
            db=db,
            incoming_message={
                "phone": advisor_phone,
                "sender_type": "advisor",
                "message": "/cerrar +5491188888888",
            },
        )

        self.assertEqual(len(router.persisted_messages), 0)
        self.assertEqual(db.commit_calls, 0)
        self.assertEqual(len(flow_manager.calls), 0)
        self.assertEqual(len(ai_provider.calls), 0)
        self.assertEqual(
            messaging_provider.sent_messages,
            [{"user": advisor_phone, "message": "No se encontró conversación activa con ese cliente."}],
        )


if __name__ == "__main__":
    unittest.main()
