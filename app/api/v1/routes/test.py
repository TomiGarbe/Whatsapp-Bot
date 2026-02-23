"""Test endpoints for validating bot flow."""

from fastapi import APIRouter

from app.providers.ai.mock_ai import MockAIProvider
from app.providers.data_sources.mock_data import MockDataSource
from app.providers.messaging.mock_messaging import MockMessagingProvider
from app.schemas.test_message import TestMessageRequest, TestMessageResponse
from app.services.bot_service import BotService

router = APIRouter()


@router.post("/test-message", response_model=TestMessageResponse)
async def test_message(payload: TestMessageRequest) -> TestMessageResponse:
    """Executes the bot flow using mock providers."""
    service = BotService(
        ai_provider=MockAIProvider(),
        data_source=MockDataSource(),
        messaging_provider=MockMessagingProvider(),
    )

    result = await service.handle_message(user=payload.user, message=payload.message)
    return TestMessageResponse(**result)

