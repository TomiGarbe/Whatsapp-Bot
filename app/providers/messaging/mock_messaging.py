"""Mock messaging provider implementation."""

from app.interfaces.messaging_provider import MessagingProvider


class MockMessagingProvider(MessagingProvider):
    """Console-based sender for local testing."""

    async def send_message(self, user: str, message: str) -> None:
        print(f"[MockMessaging] -> user={user} | message={message}")

