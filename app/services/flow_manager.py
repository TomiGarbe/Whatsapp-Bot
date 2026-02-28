"""Conversational flow manager with configurable operating modes."""

from typing import Any

from app.interfaces.data_source import DataSource
from app.services.conversation_manager import ConversationManager


class FlowManager:
    """Controls conversational state transitions and canned responses."""

    ASSISTED_MODE = "assisted"
    SUPPORTED_STATES = (
        "idle",
        "collecting_data",
        "awaiting_confirmation",
        "pending_human_validation",
        "completed",
        "cancelled",
    )

    def __init__(
        self,
        conversation_manager: ConversationManager,
        data_source: DataSource,
        mode: str,
    ) -> None:
        if mode != self.ASSISTED_MODE:
            raise ValueError(f"Unsupported mode '{mode}'. Only '{self.ASSISTED_MODE}' is available.")
        self.conversation_manager = conversation_manager
        self.data_source = data_source
        self.mode = mode
        self._request_id_by_user: dict[str, str] = {}

    async def handle(self, intent: str, user: str, message: str) -> str | None:
        """Handle one intent for a user in assisted mode."""
        current_state = self.conversation_manager.get_state(user=user)

        if intent == "greeting":
            return "Hola, soy tu asistente de WhatsApp Bot AI. En que te puedo ayudar hoy?"

        if intent == "info_request":
            items = await self.data_source.get_items()
            return self._format_item_list(items)

        if intent == "availability_request":
            return "Tenemos disponibilidad simulada para esta semana. Si quieres, iniciamos la solicitud."

        if intent == "booking_intent":
            request_payload = {
                "message": message,
                "state_before_booking": current_state,
                "mode": self.mode,
            }
            created_request = await self.data_source.create_request(user=user, data=request_payload)
            self._request_id_by_user[user] = str(created_request.get("id", ""))
            self.conversation_manager.set_state(user=user, state="collecting_data")
            return "Perfecto. Para avanzar, comparteme fecha, hora y el producto o servicio que necesitas."

        if intent == "confirmation":
            if current_state in {"collecting_data", "awaiting_confirmation"}:
                # Assisted mode requires human validation before any automatic confirmation.
                self.conversation_manager.set_state(user=user, state="pending_human_validation")
                return "Perfecto. Un asesor validara y confirmara tu solicitud en breve."
            return "Primero debes iniciar una solicitud para poder confirmarla."

        if intent == "cancellation":
            self.conversation_manager.reset_state(user=user)
            self.conversation_manager.set_state(user=user, state="cancelled")
            return "Operacion cancelada. Si quieres, puedo ayudarte a iniciar una nueva solicitud."

        # Fallback (and unknown intents) are delegated to AI provider by BotService.
        return None

    def get_last_request_id(self, user: str) -> str | None:
        """Expose request identifier for future autonomous flows."""
        return self._request_id_by_user.get(user)

    def _format_item_list(self, items: list[dict[str, Any]]) -> str:
        """Build a compact list of available items/services."""
        if not items:
            return "No hay opciones disponibles en este momento."

        lines = ["Estas son las opciones disponibles:"]
        for item in items:
            name = str(item.get("name", "Opcion sin nombre"))
            price = item.get("price", "N/A")
            item_type = str(item.get("type", "item"))
            lines.append(f"- {name} ({item_type}): ${price}")
        return "\n".join(lines)
