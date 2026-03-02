"""Azure OpenAI provider implementation."""

from __future__ import annotations

from typing import Any

from openai import AzureOpenAI

from app.core.settings import settings
from app.interfaces.ai_provider import AIProvider
from app.services.runtime_ai_context import RuntimeAIContext


class AzureAIProvider(AIProvider):
    """AI provider backed by Azure OpenAI chat completions."""

    def __init__(
        self,
        *,
        context: RuntimeAIContext,
        client: AzureOpenAI | None = None,
        deployment: str | None = None,
    ) -> None:
        self.context = context
        if client is not None:
            self.client = client
            self.deployment = deployment
            return

        if not settings.azure_openai_api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY not configured")

        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )
        self.deployment = settings.azure_openai_deployment

    async def generate_response(self, message: str, context: dict[str, Any]) -> str:
        del context
        messages = self._build_messages(user_message=message)
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return str(content) if content is not None else ""

    def _build_messages(self, *, user_message: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": self.context.build_system_prompt(),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

