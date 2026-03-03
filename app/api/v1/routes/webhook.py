"""Webhook endpoints for inbound WhatsApp Cloud API events."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.business import Business
from app.services.runtime_factory import create_bot_service

router = APIRouter()


@router.post("/webhook/messages")
async def receive_webhook(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, str]:
    """Receive webhook payload, resolve tenant, and process each message."""
    normalized_messages = _normalize_webhook_payload(payload=payload)
    for message in normalized_messages:
        try:
            business_phone = _extract_business_phone(incoming_message=message)
            business = resolve_business_by_phone(db=db, phone=business_phone)
            bot_service = create_bot_service(db=db, business=business)
            incoming_message = {
                **message,
                "business_id": str(business.id),
            }
            response = await bot_service.handle_webhook(db=db, incoming_message=incoming_message)
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"response = ": response}


def resolve_business_by_phone(db: Session, phone: str) -> Business:
    """Resolve tenant by inbound WhatsApp business number."""
    normalized_target = _normalize_phone(value=phone)
    if not normalized_target:
        raise HTTPException(status_code=404, detail="Business WhatsApp number is missing from webhook payload.")

    exact_query = (
        select(Business)
        .where(
            Business.whatsapp_number == phone.strip(),
            Business.status == "active",
        )
        .limit(1)
    )
    exact_match = db.execute(exact_query).scalars().first()
    if exact_match is not None:
        return exact_match

    candidate_query = select(Business).where(
        Business.whatsapp_number.is_not(None),
        Business.status == "active",
    )
    candidates = db.execute(candidate_query).scalars().all()
    for business in candidates:
        business_phone = business.whatsapp_number or ""
        if _normalize_phone(value=business_phone) == normalized_target:
            return business

    raise HTTPException(
        status_code=404,
        detail=f"No active business found for WhatsApp number '{phone}'.",
    )


def _normalize_webhook_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    normalized_messages: list[dict[str, Any]] = []

    # Flat payload (manual/local testing).
    if payload.get("phone") and payload.get("message"):
        business_phone = _extract_business_phone_candidate(
            payload.get("business_phone"),
            payload.get("whatsapp_number"),
            payload.get("to"),
            payload.get("phone_number_id"),
        )
        return [
            {
                "phone": payload.get("phone"),
                "message": payload.get("message"),
                "message_id": payload.get("message_id") or payload.get("id"),
                "timestamp": payload.get("timestamp"),
                "sender_type": payload.get("sender_type"),
                "is_agent": payload.get("is_agent"),
                "from_me": payload.get("from_me"),
                "business_phone": business_phone,
            }
        ]

    top_level_business_phone = _extract_business_phone_candidate(
        payload.get("business_phone"),
        payload.get("whatsapp_number"),
        payload.get("to"),
        payload.get("phone_number_id"),
    )
    base_fields = _extract_base_fields(payload=payload)

    direct_messages = payload.get("messages")
    if isinstance(direct_messages, list):
        normalized_messages.extend(
            _normalize_messages(
                messages=direct_messages,
                base_fields=base_fields,
                business_phone=top_level_business_phone,
            )
        )
        return normalized_messages

    entries = payload.get("entry")
    if not isinstance(entries, list):
        return normalized_messages

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

            metadata = value.get("metadata")
            metadata_phone = None
            if isinstance(metadata, dict):
                metadata_phone = _extract_business_phone_candidate(
                    metadata.get("display_phone_number"),
                    metadata.get("phone_number_id"),
                )

            scoped_business_phone = _extract_business_phone_candidate(
                metadata_phone,
                value.get("to"),
                top_level_business_phone,
            )
            messages = value.get("messages")
            if isinstance(messages, list):
                normalized_messages.extend(
                    _normalize_messages(
                        messages=messages,
                        base_fields=base_fields,
                        business_phone=scoped_business_phone,
                    )
                )

    return normalized_messages


def _extract_base_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "sender_type": payload.get("sender_type"),
        "is_agent": payload.get("is_agent"),
    }


def _normalize_messages(
    messages: list[Any],
    base_fields: dict[str, Any],
    business_phone: str | None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue

        text = _extract_text(message=message)
        if text is None:
            continue

        message_business_phone = _extract_business_phone_candidate(
            message.get("to"),
            message.get("phone_number_id"),
            message.get("business_phone"),
            business_phone,
        )
        normalized.append(
            {
                **base_fields,
                "phone": message.get("from") or message.get("phone"),
                "message": text,
                "message_id": message.get("id") or message.get("message_id"),
                "timestamp": message.get("timestamp"),
                "from_me": message.get("from_me"),
                "sender_type": message.get("sender_type") or base_fields.get("sender_type"),
                "business_phone": message_business_phone,
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


def _extract_business_phone(incoming_message: dict[str, Any]) -> str:
    business_phone = _extract_business_phone_candidate(
        incoming_message.get("business_phone"),
        incoming_message.get("whatsapp_number"),
        incoming_message.get("to"),
        incoming_message.get("phone_number_id"),
    )
    if business_phone is None:
        raise ValueError(
            "Unable to resolve business phone number from webhook payload. "
            "Expected metadata.display_phone_number, metadata.phone_number_id, or business_phone."
        )
    return business_phone


def _extract_business_phone_candidate(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


def _normalize_phone(*, value: str | None) -> str:
    if value is None:
        return ""
    return "".join(char for char in str(value) if char.isdigit())
