"""Mock AI provider implementation."""

from typing import Any

from app.interfaces.ai_provider import AIProvider


class MockAIProvider(AIProvider):
    """Simple AI provider used for local testing."""

    async def generate_response(self, message: str, context: dict[str, Any]) -> str:
        products = context.get("products", [])
        product_names = ", ".join(product["name"] for product in products) if products else "sin productos"
        return (
            f"Mensaje recibido: '{message}'. "
            f"Productos disponibles: {product_names}."
        )

