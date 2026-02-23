"""Interface contract for data source providers."""

from abc import ABC, abstractmethod
from typing import Any


class DataSource(ABC):
    """Defines product data operations."""

    @abstractmethod
    async def get_products(self) -> list[dict[str, Any]]:
        """Return all products available for the bot."""
        raise NotImplementedError

    @abstractmethod
    async def get_product_by_name(self, name: str) -> dict[str, Any] | None:
        """Return one product by name when available."""
        raise NotImplementedError

