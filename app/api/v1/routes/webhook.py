"""Webhook endpoints for inbound WhatsApp Cloud API events."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.providers.ai.azure_ai import AzureAIProvider
from app.providers.data_sources.mock_data import MockDataSource
from app.providers.messaging.mock_messaging import MockMessagingProvider
from app.services.bot_service import BotService
from app.services.conversation_manager import ConversationManager
from app.services.flow_manager import FlowManager
from app.services.intent_engine import IntentEngine

router = APIRouter()

intent_engine = IntentEngine()
conversation_manager = ConversationManager()
data_source = MockDataSource()
flow_manager = FlowManager(
    conversation_manager=conversation_manager,
    data_source=data_source,
    mode="assisted",
)

bot_service = BotService(
    ai_provider=AzureAIProvider(),
    messaging_provider=MockMessagingProvider(),
    intent_engine=intent_engine,
    flow_manager=flow_manager,
)


@router.post("/webhook/messages")
async def receive_webhook(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, str]:
    """Receive generic webhook payload and route it for persistence/AI handling."""
    normalized_messages = _normalize_webhook_payload(payload=payload)
    for message in normalized_messages:
        try:
            await bot_service.handle_webhook(db=db, incoming_message=message)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "accepted"}


def _normalize_webhook_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    normalized_messages: list[dict[str, Any]] = []

    # ✅ Caso 1 — Payload plano (Postman testing)
    if payload.get("phone") and payload.get("message"):
        return [payload]

    base_fields = _extract_base_fields(payload=payload)

    direct_messages = payload.get("messages")
    if isinstance(direct_messages, list):
        normalized_messages.extend(
            _normalize_messages(messages=direct_messages, base_fields=base_fields)
        )
        return normalized_messages

    entries = payload.get("entry")
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            changes = entry.get("changes")
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, dict):
                    continue
                value = change.get("value")
                if not isinstance(value, dict):
                    continue
                messages = value.get("messages")
                if isinstance(messages, list):
                    normalized_messages.extend(
                        _normalize_messages(messages=messages, base_fields=base_fields)
                    )

    return normalized_messages


def _extract_base_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "business_id": payload.get("business_id"),
        "user_id": payload.get("user_id"),
        "sender_type": payload.get("sender_type"),
        "is_agent": payload.get("is_agent"),
    }


def _normalize_messages(messages: list[Any], base_fields: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue

        text = _extract_text(message=message)
        if text is None:
            continue

        normalized.append(
            {
                **base_fields,
                "phone": message.get("from") or message.get("phone"),
                "message": text,
                "message_id": message.get("id") or message.get("message_id"),
                "timestamp": message.get("timestamp"),
                "from_me": message.get("from_me"),
                "sender_type": message.get("sender_type") or base_fields.get("sender_type"),
            }
        )
    return normalized


def _extract_text(*, message: dict[str, Any]) -> str | None:
    direct_text = message.get("message")
    if direct_text is not None and str(direct_text).strip():
        return str(direct_text).strip()

    text_payload = message.get("text")
    if isinstance(text_payload, dict):
        body = text_payload.get("body")
        if body is not None and str(body).strip():
            return str(body).strip()

    return None
