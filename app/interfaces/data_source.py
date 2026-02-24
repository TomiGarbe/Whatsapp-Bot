"""Interface contract for data source providers."""

from abc import ABC, abstractmethod
from typing import Any


class DataSource(ABC):
    """Defines generic data operations for assisted/autonomous flows."""

    @abstractmethod
    async def get_items(self) -> list[dict[str, Any]]:
        """Return a generic catalog of items (products/services)."""
        raise NotImplementedError

    @abstractmethod
    async def get_item_by_id(self, item_id: str) -> dict[str, Any] | None:
        """Return one item by identifier when available."""
        raise NotImplementedError

    @abstractmethod
    async def check_availability(self, item_id: str, datetime: str | None = None) -> bool:
        """Return item availability for an optional datetime slot."""
        raise NotImplementedError

    @abstractmethod
    async def create_request(self, user: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a booking/order request with status pending."""
        raise NotImplementedError

    @abstractmethod
    async def confirm_request(self, request_id: str) -> dict[str, Any]:
        """Confirm a previously created request."""
        raise NotImplementedError

