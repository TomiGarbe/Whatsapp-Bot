"""Unit tests for SQLDataSource lightweight retrieval scoring."""

from __future__ import annotations

import unittest
from uuid import uuid4

from app.providers.data_sources.sql_data import SQLDataSource


class _FakeSQLDataSource(SQLDataSource):
    def __init__(self, items: list[dict[str, object]]) -> None:
        self._items = items
        super().__init__(db=None, business_id=uuid4())  # type: ignore[arg-type]

    async def get_items(self) -> list[dict[str, object]]:
        return list(self._items)


class SQLDataSourceRetrievalTestCase(unittest.IsolatedAsyncioTestCase):
    """Validates LIKE + scoring retrieval behavior."""

    async def test_returns_single_match_with_highest_score(self) -> None:
        source = _FakeSQLDataSource(
            items=[
                {
                    "name": "Plan Basico",
                    "description": "Marketing mensual para pymes.",
                    "price": 100.0,
                },
                {
                    "name": "Plan Premium",
                    "description": "Incluye campañas avanzadas.",
                    "price": 250.0,
                },
            ]
        )

        result = await source.retrieve_relevant_context("basico")

        self.assertEqual(result.match_confidence, "single")
        self.assertEqual(len(result.matched_items), 1)
        self.assertEqual(result.matched_items[0]["name"], "Plan Basico")
        self.assertEqual(len(result.all_items), 2)

    async def test_returns_multiple_matches_sorted_by_score(self) -> None:
        source = _FakeSQLDataSource(
            items=[
                {
                    "name": "Plan Marketing",
                    "description": "Solucion integral de marketing.",
                    "price": 100.0,
                },
                {
                    "name": "Auditoria",
                    "description": "Diagnostico de marketing.",
                    "price": 80.0,
                },
            ]
        )

        result = await source.retrieve_relevant_context("marketing")

        self.assertEqual(result.match_confidence, "multiple")
        self.assertEqual(len(result.matched_items), 2)
        self.assertEqual(result.matched_items[0]["name"], "Plan Marketing")
        self.assertEqual(result.matched_items[1]["name"], "Auditoria")

    async def test_returns_none_when_no_match(self) -> None:
        source = _FakeSQLDataSource(
            items=[
                {
                    "name": "Plan Basico",
                    "description": "Marketing mensual para pymes.",
                    "price": 100.0,
                }
            ]
        )

        result = await source.retrieve_relevant_context("odontologia")

        self.assertEqual(result.match_confidence, "none")
        self.assertEqual(result.matched_items, [])
        self.assertEqual(len(result.all_items), 1)


if __name__ == "__main__":
    unittest.main()
