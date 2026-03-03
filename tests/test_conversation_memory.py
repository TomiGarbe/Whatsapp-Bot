"""Unit tests for conversation memory block builder."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from uuid import uuid4

from app.models.conversation import Conversation
from app.services.conversation_memory import ConversationMemoryBuilder


class _StubConversationManager:
    def __init__(self, messages: list[object]) -> None:
        self.messages = messages
        self.calls: list[dict[str, object]] = []

    async def get_recent_messages(self, *, conversation: Conversation, limit: int = 8) -> list[object]:
        self.calls.append({"conversation_id": conversation.id, "limit": limit})
        return self.messages[:limit]


class ConversationMemoryBuilderTestCase(unittest.IsolatedAsyncioTestCase):
    """Covers empty and non-empty memory block behavior."""

    def _conversation(self) -> Conversation:
        return Conversation(
            business_id=uuid4(),
            user_id=uuid4(),
            mode="assisted",
            status="active",
            control_mode="ai",
            assigned_advisor_id=None,
            context={},
        )

    async def test_returns_empty_when_history_is_too_short(self) -> None:
        manager = _StubConversationManager(
            messages=[SimpleNamespace(sender_type="user", content="Hola")],
        )
        block = await ConversationMemoryBuilder.build_memory_block(
            conversation_manager=manager,
            conversation=self._conversation(),
            limit=8,
        )
        self.assertEqual(block, "")

    async def test_builds_memory_block_with_user_and_assistant_messages(self) -> None:
        manager = _StubConversationManager(
            messages=[
                SimpleNamespace(sender_type="user", content="Hola"),
                SimpleNamespace(sender_type="assistant", content="Hola, en que te ayudo?"),
                SimpleNamespace(sender_type="system", content="interno"),
                SimpleNamespace(sender_type="user", content="Quiero un turno"),
            ],
        )
        block = await ConversationMemoryBuilder.build_memory_block(
            conversation_manager=manager,
            conversation=self._conversation(),
            limit=8,
        )
        self.assertIn("Historial reciente de la conversacion", block)
        self.assertIn("Usuario: Hola", block)
        self.assertIn("Asistente: Hola, en que te ayudo?", block)
        self.assertIn("Usuario: Quiero un turno", block)
        self.assertNotIn("interno", block)


if __name__ == "__main__":
    unittest.main()
