"""Rule-based intent detection for inbound messages with score-based ranking."""

import re
import unicodedata


class IntentEngine:
    """Detects user intent using keyword scoring and explicit tie-breaking priority."""

    def __init__(self) -> None:
        self._intent_keywords: dict[str, tuple[str, ...]] = {
            "greeting": (
                "hola",
                "hello",
                "hi",
                "buenas",
                "buenos dias",
                "buenas tardes",
                "buenas noches",
                "que tal",
                "saludos",
            ),
            "info_request": (
                "servicios",
                "producto",
                "productos",
                "plan",
                "planes",
                "precio",
                "precios",
                "catalogo",
                "informacion",
                "info",
                "que ofrecen",
                "que servicios ofrecen",
            ),
            "availability_request": (
                "disponibilidad",
                "disponible",
                "hay cupo",
                "tienen cupo",
                "hay lugar",
                "stock",
                "horario",
                "horarios",
                "turno",
                "turnos",
                "agenda",
            ),
            "booking_intent": (
                "reservar",
                "reserva",
                "agendar",
                "agendo",
                "quiero reservar",
                "sacar turno",
                "pedir cita",
                "cita",
                "contratar",
                "comprar",
                "quiero comprar",
                "me interesa",
            ),
            "confirmation": (
                "si",
                "confirmo",
                "confirmar",
                "correcto",
                "ok",
                "dale",
                "adelante",
                "aceptar",
            ),
            "cancellation": (
                "cancelar",
                "cancela",
                "anular",
                "anula",
                "detener",
                "stop",
                "olvida",
                "salir",
                "no quiero",
            ),
            "human_handoff": (
                "asesor",
                "agente",
                "humano",
                "persona",
                "representante",
                "soporte",
                "operador",
                "hablar con alguien",
                "atencion humana",
            ),
        }
        self._priority_order = (
            "human_handoff",
            "cancellation",
            "confirmation",
            "booking_intent",
            "availability_request",
            "info_request",
            "greeting",
            "fallback",
        )

    def detect_intent(self, message: str) -> str:
        """Return an intent label based on keyword score and configured priority."""
        normalized_message = self._normalize_text(message)
        scores = {
            intent: self._count_matches(normalized_message, keywords)
            for intent, keywords in self._intent_keywords.items()
        }
        best_score = max(scores.values(), default=0)
        if best_score == 0:
            return "fallback"

        tied_intents = {intent for intent, score in scores.items() if score == best_score}
        for intent in self._priority_order:
            if intent in tied_intents:
                return intent
        return "fallback"

    def _count_matches(self, message: str, keywords: tuple[str, ...]) -> int:
        """Count matched keywords in a message."""
        score = 0
        for keyword in keywords:
            if self._keyword_in_text(message, keyword):
                score += 1
        return score

    def _keyword_in_text(self, text: str, keyword: str) -> bool:
        """Match phrases by substring and single tokens by word boundary."""
        if " " in keyword:
            return keyword in text
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None

    def _normalize_text(self, message: str) -> str:
        """Normalize text to simplify robust matching."""
        lowered = message.lower().strip()
        decomposed = unicodedata.normalize("NFD", lowered)
        no_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        return re.sub(r"\s+", " ", no_accents)
