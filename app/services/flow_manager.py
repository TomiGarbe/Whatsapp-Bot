"""Conversational flow manager with configurable operating modes."""

from typing import Any
from uuid import UUID

from app.interfaces.data_source import DataSource
from app.models.conversation import Conversation
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
        business_id: UUID,
        conversation_manager: ConversationManager,
        data_source: DataSource,
        mode: str,
    ) -> None:
        if mode != self.ASSISTED_MODE:
            raise ValueError(f"Unsupported mode '{mode}'. Only '{self.ASSISTED_MODE}' is available.")
        self.business_id = business_id
        self.conversation_manager = conversation_manager
        self.data_source = data_source
        self.mode = mode

    async def handle(
        self,
        *,
        intent: str,
        user: str,
        message: str,
        conversation: Conversation,
    ) -> str | None:
        """Handle one intent for a user in assisted mode."""
        current_state = self.conversation_manager.get_state(conversation=conversation)

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
                "conversation_id": str(conversation.id),
            }
            created_request = await self.data_source.create_request(user=user, data=request_payload)
            self.conversation_manager.set_context_values(
                conversation=conversation,
                values={
                    "last_request_id": created_request.get("id"),
                    ConversationManager.STATE_CONTEXT_KEY: "collecting_data",
                },
            )
            return "Perfecto. Para avanzar, comparteme fecha, hora y el producto o servicio que necesitas."

        if intent == "confirmation":
            if current_state in {"collecting_data", "awaiting_confirmation"}:
                # Assisted mode requires human validation before any automatic confirmation.
                self.conversation_manager.set_state(
                    conversation=conversation,
                    state="pending_human_validation",
                )
                return "Perfecto. Un asesor validara y confirmara tu solicitud en breve."
            return "Primero debes iniciar una solicitud para poder confirmarla."

        if intent == "cancellation":
            self.conversation_manager.set_state(conversation=conversation, state="cancelled")
            self.conversation_manager.set_status(conversation=conversation, status="closed")
            conversation.assigned_advisor_id = None
            self.conversation_manager.set_control_mode(conversation=conversation, control_mode="ai")
            return "Operacion cancelada. Si quieres, puedo ayudarte a iniciar una nueva solicitud."

        # Fallback (and unknown intents) are delegated to AI provider by BotService.
        return None

    def get_last_request_id(self, *, conversation: Conversation) -> str | None:
        """Expose request identifier for future autonomous flows."""
        context = conversation.context if isinstance(conversation.context, dict) else {}
        request_id = context.get("last_request_id")
        if request_id is None:
            return None
        return str(request_id)

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
