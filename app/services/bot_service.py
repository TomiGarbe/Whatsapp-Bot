"""Core bot orchestration service."""

from app.interfaces.ai_provider import AIProvider
from app.interfaces.data_source import DataSource
from app.interfaces.messaging_provider import MessagingProvider


class BotService:
    """Coordinates data lookup, AI generation, and message sending."""

    def __init__(
        self,
        ai_provider: AIProvider,
        data_source: DataSource,
        messaging_provider: MessagingProvider,
    ) -> None:
        self.ai_provider = ai_provider
        self.data_source = data_source
        self.messaging_provider = messaging_provider

    async def handle_message(self, user: str, message: str) -> dict[str, str | int]:
        """Run the end-to-end bot flow for one inbound message."""
        products = await self.data_source.get_products()

        context = {
            "user": user,
            "products": products,
        }
        ai_response = await self.ai_provider.generate_response(message=message, context=context)
        await self.messaging_provider.send_message(user=user, message=ai_response)

        return {
            "user": user,
            "response": ai_response,
            "products_count": len(products),
        }

