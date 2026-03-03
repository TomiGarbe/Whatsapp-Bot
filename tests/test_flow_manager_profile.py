"""Unit tests for FlowManager behavior driven by RuntimeBusinessProfile."""

from __future__ import annotations

import unittest
from typing import Any
from uuid import uuid4

from app.models.conversation import Conversation
from app.services.conversation_manager import ConversationManager
from app.services.flow_manager import FlowManager
from app.services.runtime_business_profile import RuntimeBusinessProfile


class StubConversationManager:
    """In-memory conversation manager test double."""

    STATE_CONTEXT_KEY = ConversationManager.STATE_CONTEXT_KEY

    def get_state(self, *, conversation: Conversation) -> str:
        context = conversation.context if isinstance(conversation.context, dict) else {}
        state = context.get(self.STATE_CONTEXT_KEY)
        if isinstance(state, str) and state.strip():
            return state.strip()
        return "idle"

    def set_state(self, *, conversation: Conversation, state: str) -> None:
        context = dict(conversation.context or {})
        context[self.STATE_CONTEXT_KEY] = state
        conversation.context = context

    def set_status(self, *, conversation: Conversation, status: str) -> None:
        conversation.status = status

    def set_control_mode(self, *, conversation: Conversation, control_mode: str) -> None:
        conversation.control_mode = control_mode

    def set_context_values(self, *, conversation: Conversation, values: dict[str, Any]) -> None:
        context = dict(conversation.context or {})
        context.update(values)
        conversation.context = context


class StubDataSource:
    """Data source test double used by FlowManager tests."""

    def __init__(self) -> None:
        self.confirm_request_calls: list[str] = []
        self.create_request_calls: list[dict[str, Any]] = []

    async def get_items(self) -> list[dict[str, Any]]:
        return []

    async def get_item_by_id(self, item_id: str) -> dict[str, Any] | None:
        del item_id
        return None

    async def check_availability(self, item_id: str, datetime: str | None = None) -> bool:
        del item_id
        del datetime
        return True

    async def create_request(self, user: str, data: dict[str, Any]) -> dict[str, Any]:
        self.create_request_calls.append({"user": user, "data": data})
        return {"id": f"req-{len(self.create_request_calls)}"}

    async def confirm_request(self, request_id: str) -> dict[str, Any]:
        self.confirm_request_calls.append(request_id)
        return {"id": request_id}


class FlowManagerProfileTestCase(unittest.IsolatedAsyncioTestCase):
    """Covers mode/tone/handoff runtime behavior."""

    def _build_conversation(self) -> Conversation:
        return Conversation(
            business_id=uuid4(),
            user_id=uuid4(),
            mode="assisted",
            status="active",
            control_mode="ai",
            assigned_advisor_id=None,
            context={},
        )

    async def test_formal_tone_greeting(self) -> None:
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.ASSISTED_MODE,
            handoff_enabled=True,
            tone=RuntimeBusinessProfile.FORMAL_TONE,
        )
        manager = FlowManager(
            business_id=uuid4(),
            conversation_manager=StubConversationManager(),
            data_source=StubDataSource(),
            profile=profile,
        )

        response = await manager.handle(
            intent="greeting",
            user="+5491100000000",
            message="hola",
            conversation=self._build_conversation(),
        )

        self.assertIsInstance(response, str)
        self.assertIn("ayudarle", str(response).lower())

    async def test_assisted_mode_with_handoff_waits_for_human_validation(self) -> None:
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.ASSISTED_MODE,
            handoff_enabled=True,
            tone=RuntimeBusinessProfile.CERCANO_TONE,
        )
        conversation = self._build_conversation()
        conversation.context = {
            ConversationManager.STATE_CONTEXT_KEY: "collecting_data",
            "last_request_id": "req-100",
        }
        data_source = StubDataSource()
        manager = FlowManager(
            business_id=conversation.business_id,
            conversation_manager=StubConversationManager(),
            data_source=data_source,
            profile=profile,
        )

        response = await manager.handle(
            intent="confirmation",
            user="+5491100000000",
            message="confirmo",
            conversation=conversation,
        )

        self.assertEqual(
            conversation.context.get(ConversationManager.STATE_CONTEXT_KEY),
            "pending_human_validation",
        )
        self.assertEqual(data_source.confirm_request_calls, [])
        self.assertIn("asesor", str(response).lower())

    async def test_assisted_mode_without_handoff_confirms_automatically(self) -> None:
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.ASSISTED_MODE,
            handoff_enabled=False,
            tone=RuntimeBusinessProfile.CERCANO_TONE,
        )
        conversation = self._build_conversation()
        conversation.context = {
            ConversationManager.STATE_CONTEXT_KEY: "collecting_data",
            "last_request_id": "req-101",
        }
        data_source = StubDataSource()
        manager = FlowManager(
            business_id=conversation.business_id,
            conversation_manager=StubConversationManager(),
            data_source=data_source,
            profile=profile,
        )

        response = await manager.handle(
            intent="confirmation",
            user="+5491100000000",
            message="confirmo",
            conversation=conversation,
        )

        self.assertEqual(data_source.confirm_request_calls, ["req-101"])
        self.assertEqual(
            conversation.context.get(ConversationManager.STATE_CONTEXT_KEY),
            "completed",
        )
        self.assertIn("confirmada", str(response).lower())

    async def test_autonomous_mode_confirms_automatically(self) -> None:
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.AUTONOMOUS_MODE,
            handoff_enabled=True,
            tone=RuntimeBusinessProfile.FORMAL_TONE,
        )
        conversation = self._build_conversation()
        conversation.context = {
            ConversationManager.STATE_CONTEXT_KEY: "collecting_data",
            "last_request_id": "req-102",
        }
        data_source = StubDataSource()
        manager = FlowManager(
            business_id=conversation.business_id,
            conversation_manager=StubConversationManager(),
            data_source=data_source,
            profile=profile,
        )

        response = await manager.handle(
            intent="confirmation",
            user="+5491100000000",
            message="confirmo",
            conversation=conversation,
        )

        self.assertEqual(data_source.confirm_request_calls, ["req-102"])
        self.assertEqual(
            conversation.context.get(ConversationManager.STATE_CONTEXT_KEY),
            "completed",
        )
        self.assertIn("ha sido confirmada", str(response).lower())

    async def test_handoff_intent_is_blocked_when_profile_disables_it(self) -> None:
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.ASSISTED_MODE,
            handoff_enabled=False,
            tone=RuntimeBusinessProfile.FORMAL_TONE,
        )
        manager = FlowManager(
            business_id=uuid4(),
            conversation_manager=StubConversationManager(),
            data_source=StubDataSource(),
            profile=profile,
        )

        decision = manager.evaluate_handoff(intent="human_handoff")

        self.assertFalse(decision.should_route_to_human)
        self.assertIsNotNone(decision.blocked_message)
        self.assertIn("no tenemos derivacion", str(decision.blocked_message).lower())


if __name__ == "__main__":
    unittest.main()
