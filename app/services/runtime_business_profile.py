"""Runtime-ready business profile built from persisted business configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.business import BusinessConfig


@dataclass(frozen=True)
class RuntimeBusinessProfile:
    """Normalized runtime profile consumed by request-scoped services."""

    ASSISTED_MODE = "assisted"
    AUTONOMOUS_MODE = "autonomous"
    CERCANO_TONE = "cercano"
    FORMAL_TONE = "formal"
    _SUPPORTED_MODES = {ASSISTED_MODE, AUTONOMOUS_MODE}
    _SUPPORTED_TONES = {CERCANO_TONE, FORMAL_TONE}

    mode: str = ASSISTED_MODE
    handoff_enabled: bool = True
    tone: str = CERCANO_TONE

    @classmethod
    def from_business_config(
        cls,
        *,
        business_config: BusinessConfig | None,
    ) -> "RuntimeBusinessProfile":
        """Build a runtime profile from DB config with defensive normalization."""
        if business_config is None:
            return cls()

        mode = cls._normalize_mode(business_config.mode)
        tone = cls._resolve_tone(
            mode=mode,
            assisted_config=business_config.assisted_config,
            autonomous_config=business_config.autonomous_config,
        )
        return cls(
            mode=mode,
            handoff_enabled=bool(business_config.handoff_enabled),
            tone=tone,
        )

    @classmethod
    def _normalize_mode(cls, raw_mode: Any) -> str:
        if not isinstance(raw_mode, str):
            return cls.ASSISTED_MODE

        normalized_mode = raw_mode.strip().lower()
        if normalized_mode not in cls._SUPPORTED_MODES:
            return cls.ASSISTED_MODE
        return normalized_mode

    @classmethod
    def _resolve_tone(
        cls,
        *,
        mode: str,
        assisted_config: Any,
        autonomous_config: Any,
    ) -> str:
        assisted = cls._as_dict(assisted_config)
        autonomous = cls._as_dict(autonomous_config)
        mode_config = assisted if mode == cls.ASSISTED_MODE else autonomous

        for raw_tone in (
            mode_config.get("tone"),
            assisted.get("tone"),
            autonomous.get("tone"),
        ):
            tone = cls._normalize_tone(raw_tone)
            if tone is not None:
                return tone
        return cls.CERCANO_TONE

    @classmethod
    def _normalize_tone(cls, raw_tone: Any) -> str | None:
        if not isinstance(raw_tone, str):
            return None
        normalized_tone = raw_tone.strip().lower()
        if normalized_tone not in cls._SUPPORTED_TONES:
            return None
        return normalized_tone

    @staticmethod
    def _as_dict(raw_value: Any) -> dict[str, Any]:
        if isinstance(raw_value, dict):
            return raw_value
        return {}

