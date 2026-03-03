"""Conversation flow manager driven by runtime business profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.interfaces.data_source import DataSource
from app.models.conversation import Conversation
from app.services.conversation_manager import ConversationManager
from app.services.runtime_business_profile import RuntimeBusinessProfile


@dataclass(frozen=True)
class HandoffDecision:
    """Encapsulates handoff routing decision for one user intent."""

    should_route_to_human: bool
    blocked_message: str | None = None


class FlowManager:
    """Controls flow state and business-specific responses."""

    ASSISTED_MODE = RuntimeBusinessProfile.ASSISTED_MODE
    AUTONOMOUS_MODE = RuntimeBusinessProfile.AUTONOMOUS_MODE
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
        profile: RuntimeBusinessProfile | None = None,
        mode: str | None = None,
    ) -> None:
        self.business_id = business_id
        self.conversation_manager = conversation_manager
        self.data_source = data_source
        if profile is None:
            profile = RuntimeBusinessProfile(mode=self._normalize_legacy_mode(mode))
        self.profile = profile

    async def handle(
        self,
        *,
        intent: str,
        user: str,
        message: str,
        conversation: Conversation,
    ) -> str | None:
        """Handle one intent using the configured runtime profile."""
        current_state = self.conversation_manager.get_state(conversation=conversation)

        if intent == "human_handoff" and not self.handoff_enabled:
            return self._message("handoff_disabled")

        if intent == "greeting":
            return self._message("greeting")

        if intent == "info_request":
            items = await self.data_source.get_items()
            return self._format_item_list(items)

        if intent == "availability_request":
            return self._message("availability")

        if intent == "booking_intent":
            request_payload = {
                "message": message,
                "state_before_booking": current_state,
                "mode": self.mode,
                "conversation_id": str(conversation.id),
                "human_validation_required": self._human_validation_required(),
            }
            created_request = await self.data_source.create_request(user=user, data=request_payload)
            self.conversation_manager.set_context_values(
                conversation=conversation,
                values={
                    "last_request_id": created_request.get("id"),
                    ConversationManager.STATE_CONTEXT_KEY: "collecting_data",
                },
            )
            return self._message("booking_prompt")

        if intent == "confirmation":
            return await self._handle_confirmation(conversation=conversation, current_state=current_state)

        if intent == "cancellation":
            self.conversation_manager.set_state(conversation=conversation, state="cancelled")
            self.conversation_manager.set_status(conversation=conversation, status="closed")
            conversation.assigned_advisor_id = None
            self.conversation_manager.set_control_mode(conversation=conversation, control_mode="ai")
            return self._message("cancellation")

        # Fallback (and unknown intents) are delegated to AI provider by BotService.
        return None

    @property
    def mode(self) -> str:
        """Expose current operating mode for router/context compatibility."""
        return self.profile.mode

    @property
    def handoff_enabled(self) -> bool:
        """Expose whether human handoff is available for this business."""
        return self.profile.handoff_enabled

    def evaluate_handoff(self, *, intent: str) -> HandoffDecision:
        """Return handoff routing decision for one detected intent."""
        if intent != "human_handoff":
            return HandoffDecision(should_route_to_human=False)
        if not self.handoff_enabled:
            return HandoffDecision(
                should_route_to_human=False,
                blocked_message=self._message("handoff_disabled"),
            )
        return HandoffDecision(should_route_to_human=True)

    def get_handoff_acknowledgement(self) -> str:
        """Return user-facing confirmation when conversation is routed to a human."""
        return self._message("handoff_acknowledged")

    def get_last_request_id(self, *, conversation: Conversation) -> str | None:
        """Expose request identifier for future autonomous flows."""
        context = conversation.context if isinstance(conversation.context, dict) else {}
        request_id = context.get("last_request_id")
        if request_id is None:
            return None
        return str(request_id)

    async def _handle_confirmation(self, *, conversation: Conversation, current_state: str) -> str:
        if current_state not in {"collecting_data", "awaiting_confirmation"}:
            return self._message("confirmation_missing_request")

        if self.mode == self.AUTONOMOUS_MODE:
            return await self._confirm_request_automatically(conversation=conversation)

        if self.handoff_enabled:
            self.conversation_manager.set_state(
                conversation=conversation,
                state="pending_human_validation",
            )
            return self._message("confirmation_waiting_human")

        return await self._confirm_request_automatically(conversation=conversation)

    async def _confirm_request_automatically(self, *, conversation: Conversation) -> str:
        request_id = self.get_last_request_id(conversation=conversation)
        if request_id is None:
            return self._message("confirmation_missing_request")

        try:
            await self.data_source.confirm_request(request_id=request_id)
        except ValueError:
            return self._message("confirmation_not_found")

        self.conversation_manager.set_state(conversation=conversation, state="completed")
        return self._message("confirmation_success")

    def _human_validation_required(self) -> bool:
        return self.mode == self.ASSISTED_MODE and self.handoff_enabled

    def _normalize_legacy_mode(self, raw_mode: str | None) -> str:
        if not isinstance(raw_mode, str):
            return self.ASSISTED_MODE
        normalized_mode = raw_mode.strip().lower()
        if normalized_mode not in {self.ASSISTED_MODE, self.AUTONOMOUS_MODE}:
            return self.ASSISTED_MODE
        return normalized_mode

    def _format_item_list(self, items: list[dict[str, Any]]) -> str:
        """Build a compact list of available items/services."""
        if not items:
            return self._message("no_items")

        lines = [self._message("item_list_intro")]
        for item in items:
            name = str(item.get("name", "Opcion sin nombre"))
            price = item.get("price", "N/A")
            item_type = str(item.get("type", "item"))
            lines.append(f"- {name} ({item_type}): ${price}")
        return "\n".join(lines)

    def _message(self, key: str) -> str:
        tone_map = self._messages_by_tone().get(self.profile.tone, {})
        default_map = self._messages_by_tone()[RuntimeBusinessProfile.CERCANO_TONE]
        message = tone_map.get(key) or default_map.get(key)
        if message is None:
            raise KeyError(f"Missing message key '{key}' for tone '{self.profile.tone}'.")
        return message

    def _messages_by_tone(self) -> dict[str, dict[str, str]]:
        return {
            RuntimeBusinessProfile.CERCANO_TONE: {
                "greeting": "Hola, soy tu asistente de WhatsApp Bot AI. En que te puedo ayudar hoy?",
                "availability": "Tenemos disponibilidad simulada para esta semana. Si quieres, iniciamos la solicitud.",
                "booking_prompt": "Perfecto. Para avanzar, comparteme fecha, hora y el producto o servicio que necesitas.",
                "confirmation_waiting_human": "Perfecto. Un asesor validara y confirmara tu solicitud en breve.",
                "confirmation_success": "Listo. Tu solicitud quedo confirmada.",
                "confirmation_not_found": "No pude encontrar tu solicitud para confirmarla. Si quieres, la iniciamos de nuevo.",
                "confirmation_missing_request": "Primero debes iniciar una solicitud para poder confirmarla.",
                "cancellation": "Operacion cancelada. Si quieres, puedo ayudarte a iniciar una nueva solicitud.",
                "handoff_disabled": "En este momento no tenemos derivacion a asesores. Puedo seguir ayudandote por aqui.",
                "handoff_acknowledged": "Te paso con un asesor para continuar la conversacion.",
                "no_items": "No hay opciones disponibles en este momento.",
                "item_list_intro": "Estas son las opciones disponibles:",
            },
            RuntimeBusinessProfile.FORMAL_TONE: {
                "greeting": "Hola. Soy el asistente de WhatsApp Bot AI. En que puedo ayudarle hoy?",
                "availability": "Contamos con disponibilidad simulada para esta semana. Si lo desea, iniciamos su solicitud.",
                "booking_prompt": "De acuerdo. Para continuar, comparta fecha, hora y el producto o servicio requerido.",
                "confirmation_waiting_human": "Su solicitud sera validada por un asesor y confirmada a la brevedad.",
                "confirmation_success": "Su solicitud ha sido confirmada.",
                "confirmation_not_found": "No fue posible localizar su solicitud para confirmarla. Si lo desea, podemos iniciarla nuevamente.",
                "confirmation_missing_request": "Primero debe iniciar una solicitud para poder confirmarla.",
                "cancellation": "Operacion cancelada. Si lo desea, puedo ayudarle a iniciar una nueva solicitud.",
                "handoff_disabled": "Actualmente no tenemos derivacion a asesores. Puedo continuar asistiendole por este medio.",
                "handoff_acknowledged": "La conversacion sera transferida a un asesor para continuar la atencion.",
                "no_items": "No hay opciones disponibles en este momento.",
                "item_list_intro": "Estas son las opciones disponibles:",
            },
        }
