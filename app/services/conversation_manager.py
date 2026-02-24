"""Conversation state manager stored in memory."""


class ConversationManager:
    """Tracks per-user conversation state in RAM."""

    def __init__(self) -> None:
        self._conversations: dict[str, dict[str, str]] = {}

    def get_state(self, user: str) -> str:
        """Return current state for user, defaulting to idle."""
        conversation = self._conversations.get(user)
        if conversation is None:
            self._conversations[user] = {"state": "idle"}
            return "idle"
        return conversation.get("state", "idle")

    def set_state(self, user: str, state: str) -> None:
        """Set the state for a user conversation."""
        self._conversations[user] = {"state": state}

    def reset_state(self, user: str) -> None:
        """Clear user state from memory."""
        self._conversations.pop(user, None)

