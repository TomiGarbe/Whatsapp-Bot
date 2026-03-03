"""Azure OpenAI provider implementation."""

from __future__ import annotations

from typing import Any

from openai import AzureOpenAI

from app.core.settings import settings
from app.interfaces.ai_provider import AIProvider
from app.services.retrieval import RetrievalResult
from app.services.runtime_ai_context import RuntimeAIContext
from app.services.runtime_business_profile import RuntimeBusinessProfile


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
        return self._generate_from_messages(messages=messages)

    async def generate_with_retrieval(
        self,
        *,
        user_message: str,
        retrieval: RetrievalResult,
        profile: RuntimeBusinessProfile,
        memory_block: str = "",
    ) -> str:
        messages = self._build_messages_with_retrieval(
            user_message=user_message,
            retrieval=retrieval,
            profile=profile,
            memory_block=memory_block,
        )
        return self._generate_from_messages(messages=messages)

    def _generate_from_messages(self, *, messages: list[dict[str, str]]) -> str:
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

    def _build_messages_with_retrieval(
        self,
        *,
        user_message: str,
        retrieval: RetrievalResult,
        profile: RuntimeBusinessProfile,
        memory_block: str,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self.context.build_system_prompt(),
            },
        ]
        if memory_block.strip():
            messages.append(
                {
                    "role": "system",
                    "content": memory_block,
                }
            )
        messages.append(
            {
                "role": "system",
                "content": self._build_retrieval_context_message(
                    retrieval=retrieval,
                    profile=profile,
                ),
            }
        )
        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )
        return messages

    def _build_retrieval_context_message(
        self,
        *,
        retrieval: RetrievalResult,
        profile: RuntimeBusinessProfile,
    ) -> str:
        include_price = profile.show_prices
        matched_items = self._sanitize_items_for_context(
            items=retrieval.matched_items,
            include_price=include_price,
        )
        all_items = self._sanitize_items_for_context(
            items=retrieval.all_items,
            include_price=include_price,
        )

        lines = [
            "Contexto del negocio:",
            f"- Nivel de coincidencia: {retrieval.match_confidence}",
        ]
        if retrieval.match_confidence == "none":
            lines.append("- No hubo coincidencia exacta con la consulta del usuario.")
            lines.append("Catalogo completo:")
            lines.extend(self._format_items_for_prompt(items=all_items, include_price=include_price))
            return "\n".join(lines)

        lines.append("Coincidencias encontradas:")
        lines.extend(self._format_items_for_prompt(items=matched_items, include_price=include_price))
        return "\n".join(lines)

    def _sanitize_items_for_context(
        self,
        *,
        items: list[dict[str, Any]],
        include_price: bool,
    ) -> list[dict[str, Any]]:
        sanitized_items: list[dict[str, Any]] = []
        for item in items:
            sanitized_item = {
                "name": str(item.get("name", "Item sin nombre")),
                "description": str(item.get("description") or "Sin descripcion"),
            }
            if include_price:
                sanitized_item["price"] = item.get("price")
                sanitized_item["currency"] = item.get("currency")
            sanitized_items.append(sanitized_item)
        return sanitized_items

    def _format_items_for_prompt(
        self,
        *,
        items: list[dict[str, Any]],
        include_price: bool,
    ) -> list[str]:
        if not items:
            return ["- Sin items disponibles."]

        lines: list[str] = []
        for item in items:
            lines.append(f"- Nombre: {item.get('name', 'Item sin nombre')}")
            lines.append(f"  Descripcion: {item.get('description', 'Sin descripcion')}")
            if include_price:
                lines.append(f"  Precio: {item.get('price', 'N/A')}")
        return lines
