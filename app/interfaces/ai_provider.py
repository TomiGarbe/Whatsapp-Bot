"""Interface contract for AI providers."""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Defines AI provider behavior."""

    @abstractmethod
    async def generate_response(self, message: str, context: dict[str, Any]) -> str:
        """Generate a response based on user message and context."""
        raise NotImplementedError

