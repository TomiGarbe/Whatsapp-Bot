"""Test endpoints for validating bot flow."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.providers.ai.mock_ai import MockAIProvider
from app.providers.data_sources.mock_data import MockDataSource
from app.providers.messaging.mock_messaging import MockMessagingProvider
from app.schemas.test_message import TestMessageRequest, TestMessageResponse
from app.services.bot_service import BotService
from app.services.conversation_manager import ConversationManager
from app.services.flow_manager import FlowManager
from app.services.intent_engine import IntentEngine

router = APIRouter()

# Shared service instances for local test execution.
intent_engine = IntentEngine()
conversation_manager = ConversationManager()
data_source = MockDataSource()
flow_manager = FlowManager(
    conversation_manager=conversation_manager,
    data_source=data_source,
    mode="assisted",
)

bot_service = BotService(
    ai_provider=MockAIProvider(),
    messaging_provider=MockMessagingProvider(),
    intent_engine=intent_engine,
    flow_manager=flow_manager,
)


@router.post("/test-message", response_model=TestMessageResponse)
async def test_message(payload: TestMessageRequest, db: Session = Depends(get_db)) -> TestMessageResponse:
    """Executes the bot flow using mock providers."""
    result = await bot_service.handle_message(
        db=db,
        business_id=str(payload.business_id),
        user_id=str(payload.user_id),
        user=payload.user,
        message=payload.message,
    )
    return TestMessageResponse(**result)

