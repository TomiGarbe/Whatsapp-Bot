"""Mock data source implementation."""

from typing import Any

from app.interfaces.data_source import DataSource


class MockDataSource(DataSource):
    """In-memory data source with generic catalog and request lifecycle."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = [
            {"id": "1", "name": "Consulta Inicial", "price": 50, "type": "service"},
            {"id": "2", "name": "Plan Premium", "price": 120, "type": "service"},
            {"id": "3", "name": "Sesion de Seguimiento", "price": 80, "type": "meeting"},
        ]
        self._requests: dict[str, dict[str, Any]] = {}
        self._request_sequence = 0

    async def get_items(self) -> list[dict[str, Any]]:
        return self._items

    async def get_item_by_id(self, item_id: str) -> dict[str, Any] | None:
        for item in self._items:
            if item.get("id") == item_id:
                return item
        return None

    async def check_availability(self, item_id: str, datetime: str | None = None) -> bool:
        del item_id
        del datetime
        return True

    async def create_request(self, user: str, data: dict[str, Any]) -> dict[str, Any]:
        self._request_sequence += 1
        request_id = str(self._request_sequence)
        request = {
            "id": request_id,
            "user": user,
            "data": data,
            "status": "pending",
        }
        self._requests[request_id] = request
        return request

    async def confirm_request(self, request_id: str) -> dict[str, Any]:
        request = self._requests.get(request_id)
        if request is None:
            raise ValueError(f"Request '{request_id}' not found.")
        request["status"] = "confirmed"
        self._requests[request_id] = request
        return request

    async def get_request_by_id(self, request_id: str) -> dict[str, Any] | None:
        """Helper for tests/debugging; not part of DataSource contract."""
        return self._requests.get(request_id)

    async def get_requests(self) -> list[dict[str, Any]]:
        """Helper for tests/debugging; not part of DataSource contract."""
        return list(self._requests.values())

