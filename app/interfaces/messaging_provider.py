"""Interface contract for messaging providers."""

from abc import ABC, abstractmethod


class MessagingProvider(ABC):
    """Defines outbound message delivery behavior."""

    @abstractmethod
    async def send_message(self, user: str, message: str) -> None:
        """Send a message to a target user."""
        raise NotImplementedError

