"""Conversation state manager stored in memory."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConversationContext:
    """In-memory representation of an active conversation."""

    user: str
    state: str = "idle"


class ConversationManager:
    """Tracks per-user conversation state in RAM."""

    def __init__(self) -> None:
        self._conversations: dict[str, ConversationContext] = {}

    def get_or_create_active_conversation(self, user: str) -> ConversationContext:
        """Return active conversation for a user, creating one if missing."""
        conversation = self._conversations.get(user)
        if conversation is None:
            conversation = ConversationContext(user=user)
            self._conversations[user] = conversation
        return conversation

    def get_state(self, user: str) -> str:
        """Return current state for user, defaulting to idle."""
        conversation = self.get_or_create_active_conversation(user=user)
        return conversation.state

    def set_state(self, user: str, state: str) -> None:
        """Set the state for a user conversation."""
        conversation = self.get_or_create_active_conversation(user=user)
        conversation.state = state

    def reset_state(self, user: str) -> None:
        """Clear user state from memory."""
        self._conversations.pop(user, None)

