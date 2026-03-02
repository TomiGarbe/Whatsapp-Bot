"""Conversation memory block builder for AI prompts."""

from __future__ import annotations

from app.models.conversation import Conversation


class ConversationMemoryBuilder:
    """Builds a compact recent-history text block for AI context."""

    @staticmethod
    async def build_memory_block(
        *,
        conversation_manager,
        conversation: Conversation,
        limit: int = 8,
    ) -> str:
        get_recent = getattr(conversation_manager, "get_recent_messages", None)
        if not callable(get_recent):
            return ""

        recent_messages = await get_recent(conversation=conversation, limit=limit)
        if len(recent_messages) <= 1:
            return ""

        lines = ["Historial reciente de la conversacion:", ""]
        for message in recent_messages:
            sender_type = getattr(message, "sender_type", "")
            if sender_type == "user":
                label = "Usuario"
            elif sender_type == "assistant":
                label = "Asistente"
            else:
                continue

            content = str(getattr(message, "content", "")).strip()
            if not content:
                continue
            lines.append(f"{label}: {content}")

        if len(lines) <= 2:
            return ""
        return "\n".join(lines)

