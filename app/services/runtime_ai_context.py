"""Runtime AI context that captures business identity and behavior instructions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.runtime_business_profile import RuntimeBusinessProfile


@dataclass(frozen=True)
class RuntimeAIContext:
    """Immutable AI context built once per request/business."""

    business_name: str
    industry: str
    tone: str
    mode: str

    @classmethod
    def from_business(
        cls,
        *,
        business: Any,
        profile: RuntimeBusinessProfile,
    ) -> "RuntimeAIContext":
        """Create a context from already-loaded business data and runtime profile."""
        business_name = cls._normalized_or_default(
            value=getattr(business, "name", None),
            default="el negocio",
        )
        industry = cls._normalized_or_default(
            value=getattr(business, "industry", None),
            default="servicios",
        )
        tone = cls._normalize_tone(value=getattr(profile, "tone", None))
        mode = cls._normalize_mode(value=getattr(profile, "mode", None))
        return cls(
            business_name=business_name,
            industry=industry,
            tone=tone,
            mode=mode,
        )

    def build_system_prompt(self) -> str:
        """Return system prompt for AI provider calls."""
        sections = [
            f"Eres el asistente virtual oficial de {self.business_name}.",
            f"Rubro del negocio: {self.industry}.",
            f"Modo operativo actual: {self.mode}.",
            self._tone_instructions(),
            self._mode_instructions(),
            "Reglas comerciales obligatorias:",
            "- No prometas resultados garantizados ni tiempos exactos no confirmados.",
            "- No inventes informacion sobre productos, precios, disponibilidad o politicas.",
            "- Si falta informacion, dilo explicitamente y solicita solo el dato minimo necesario.",
            "- Cuando sea apropiado, orienta la conversacion al siguiente paso comercial concreto.",
            "Responde en espanol, de forma clara y util.",
        ]
        return "\n".join(sections)

    def _tone_instructions(self) -> str:
        """Return tone-specific instruction block."""
        if self.tone == RuntimeBusinessProfile.FORMAL_TONE:
            return (
                "Tono: formal. Usa trato de usted, redaccion sobria y profesional, "
                "sin modismos ni exceso de confianza."
            )
        return (
            "Tono: cercano. Usa trato cordial y directo, lenguaje simple y humano, "
            "manteniendo profesionalismo."
        )

    def _mode_instructions(self) -> str:
        """Return mode-specific operational constraints."""
        if self.mode == RuntimeBusinessProfile.AUTONOMOUS_MODE:
            return (
                "Modo autonomous: puedes guiar el proceso de forma automatica y confirmar "
                "pasos cuando haya datos suficientes."
            )
        return (
            "Modo assisted: no confirmes acciones sensibles por cuenta propia; cuando corresponda, "
            "indica que un asesor debe validar o finalizar la gestion."
        )

    @staticmethod
    def _normalized_or_default(*, value: Any, default: str) -> str:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
        return default

    @staticmethod
    def _normalize_tone(*, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {
                RuntimeBusinessProfile.CERCANO_TONE,
                RuntimeBusinessProfile.FORMAL_TONE,
            }:
                return normalized
        return RuntimeBusinessProfile.CERCANO_TONE

    @staticmethod
    def _normalize_mode(*, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {
                RuntimeBusinessProfile.ASSISTED_MODE,
                RuntimeBusinessProfile.AUTONOMOUS_MODE,
            }:
                return normalized
        return RuntimeBusinessProfile.ASSISTED_MODE

