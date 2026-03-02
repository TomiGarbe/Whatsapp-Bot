"""Conversation state manager backed by the conversations table."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message


class ConversationManager:
    """Persists conversational state and metadata in PostgreSQL."""

    STATE_CONTEXT_KEY = "flow_state"

    def __init__(self, db: Session, business_id: UUID) -> None:
        self.db = db
        self.business_id = business_id

    def get_state(self, *, conversation: Conversation) -> str:
        """Return current flow state from conversation context."""
        self._assert_business_scope(conversation=conversation)
        context = self._as_context_dict(conversation.context)
        raw_state = context.get(self.STATE_CONTEXT_KEY)
        if isinstance(raw_state, str) and raw_state.strip():
            return raw_state.strip()
        return "idle"

    def set_state(self, *, conversation: Conversation, state: str) -> None:
        """Persist flow state in conversation context."""
        self._assert_business_scope(conversation=conversation)
        context = self._as_context_dict(conversation.context)
        context[self.STATE_CONTEXT_KEY] = state
        conversation.context = context
        self._persist(conversation=conversation)

    def reset_state(self, *, conversation: Conversation) -> None:
        """Remove flow state from conversation context."""
        self._assert_business_scope(conversation=conversation)
        context = self._as_context_dict(conversation.context)
        if self.STATE_CONTEXT_KEY in context:
            context.pop(self.STATE_CONTEXT_KEY, None)
            conversation.context = context
            self._persist(conversation=conversation)

    def set_status(self, *, conversation: Conversation, status: str) -> None:
        """Persist conversation lifecycle status."""
        self._assert_business_scope(conversation=conversation)
        conversation.status = status
        self._persist(conversation=conversation)

    def set_control_mode(self, *, conversation: Conversation, control_mode: str) -> None:
        """Persist conversation control mode (ai/human)."""
        self._assert_business_scope(conversation=conversation)
        conversation.control_mode = control_mode
        self._persist(conversation=conversation)

    def set_context_values(self, *, conversation: Conversation, values: dict[str, Any]) -> None:
        """Merge context values and persist conversation."""
        self._assert_business_scope(conversation=conversation)
        context = self._as_context_dict(conversation.context)
        context.update(values)
        conversation.context = context
        self._persist(conversation=conversation)

    async def get_recent_messages(
        self,
        *,
        conversation: Conversation,
        limit: int = 8,
    ) -> list[Message]:
        """Return recent user/assistant messages in chronological order."""
        self._assert_business_scope(conversation=conversation)
        if limit <= 0:
            return []

        query = (
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.sender_type.in_(("user", "assistant")),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        recent_desc = self.db.execute(query).scalars().all()
        return list(reversed(recent_desc))

    def _persist(self, *, conversation: Conversation) -> None:
        self.db.add(conversation)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _assert_business_scope(self, *, conversation: Conversation) -> None:
        if conversation.business_id != self.business_id:
            raise ValueError("Conversation does not belong to the configured business scope.")

    def _as_context_dict(self, context: Any) -> dict[str, Any]:
        if isinstance(context, dict):
            return dict(context)
        return {}

