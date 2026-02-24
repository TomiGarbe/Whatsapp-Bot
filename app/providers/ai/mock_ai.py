"""Mock AI provider implementation."""

from typing import Any

from app.interfaces.ai_provider import AIProvider


class MockAIProvider(AIProvider):
    """Simple AI provider used for local testing."""

    async def generate_response(self, message: str, context: dict[str, Any]) -> str:
        del message
        del context
        return "[MOCK AI] No entendi tu solicitud. Puedes reformularla?"

