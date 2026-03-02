"""Test endpoints for validating bot flow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.business import Business
from app.schemas.test_message import TestMessageRequest, TestMessageResponse
from app.services.runtime_factory import create_bot_service

router = APIRouter()


@router.post("/test-message", response_model=TestMessageResponse)
async def test_message(payload: TestMessageRequest, db: Session = Depends(get_db)) -> TestMessageResponse:
    """Executes the bot flow using request-scoped tenant dependencies."""
    business_query = select(Business).where(Business.id == payload.business_id).limit(1)
    business = db.execute(business_query).scalars().first()
    if business is None:
        raise HTTPException(status_code=404, detail=f"Business '{payload.business_id}' does not exist.")

    bot_service = create_bot_service(db=db, business=business)
    await bot_service.handle_webhook(
        db=db,
        incoming_message={
            "business_id": str(payload.business_id),
            "user_id": str(payload.user_id),
            "phone": payload.user,
            "message": payload.message,
            "sender_type": "user",
        },
    )
    response = bot_service.message_router.get_last_response(user=payload.user) or ""
    return TestMessageResponse(user=payload.user, response=response)

