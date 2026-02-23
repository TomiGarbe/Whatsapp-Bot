"""Mock data source implementation."""

from typing import Any

from app.interfaces.data_source import DataSource


class MockDataSource(DataSource):
    """In-memory product catalog for testing."""

    def __init__(self) -> None:
        self._products: list[dict[str, Any]] = [
            {"id": 1, "name": "Plan Starter", "price": 29},
            {"id": 2, "name": "Plan Pro", "price": 79},
            {"id": 3, "name": "Plan Enterprise", "price": 199},
        ]

    async def get_products(self) -> list[dict[str, Any]]:
        return self._products

    async def get_product_by_name(self, name: str) -> dict[str, Any] | None:
        target = name.strip().lower()
        for product in self._products:
            if product["name"].lower() == target:
                return product
        return None

