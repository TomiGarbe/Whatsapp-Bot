"""Mock AI provider implementation."""

from typing import Any

from app.interfaces.ai_provider import AIProvider
from app.services.retrieval import RetrievalResult
from app.services.runtime_business_profile import RuntimeBusinessProfile


class MockAIProvider(AIProvider):
    """Simple AI provider used for local testing."""

    async def generate_response(self, message: str, context: dict[str, Any]) -> str:
        del message
        del context
        return "[MOCK AI] No entendi tu solicitud. Puedes reformularla?"

    async def generate_with_retrieval(
        self,
        *,
        user_message: str,
        retrieval: RetrievalResult,
        profile: RuntimeBusinessProfile,
        memory_block: str = "",
    ) -> str:
        del user_message
        del retrieval
        del profile
        del memory_block
        return "[MOCK AI] No entendi tu solicitud. Puedes reformularla?"

