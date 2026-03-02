"""Per-request dependency factory for tenant-aware bot runtime."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.business import Business, BusinessConfig
from app.providers.ai.azure_ai import AzureAIProvider
from app.providers.ai.mock_ai import MockAIProvider
from app.providers.data_sources.sql_data import SQLDataSource
from app.providers.messaging.mock_messaging import MockMessagingProvider
from app.providers.messaging.whatsapp_cloud import WhatsAppCloudProvider
from app.services.bot_service import BotService
from app.services.conversation_manager import ConversationManager
from app.services.flow_manager import FlowManager
from app.services.intent_engine import IntentEngine
from app.services.runtime_business_profile import RuntimeBusinessProfile


def create_bot_service(*, db: Session, business: Business) -> BotService:
    """Build a fresh bot service graph for one inbound message."""
    business_config = _get_business_config(db=db, business_id=business.id)
    profile = RuntimeBusinessProfile.from_business_config(business_config=business_config)
    data_source = SQLDataSource(db=db, business_id=business.id)
    conversation_manager = ConversationManager(db=db, business_id=business.id)
    flow_manager = FlowManager(
        business_id=business.id,
        conversation_manager=conversation_manager,
        data_source=data_source,
        profile=profile,
    )

    return BotService(
        ai_provider=create_ai_provider(),
        messaging_provider=create_messaging_provider(
            business_whatsapp_number=business.whatsapp_number,
        ),
        intent_engine=IntentEngine(),
        flow_manager=flow_manager,
    )


def create_ai_provider():
    """Select AI provider based on runtime configuration."""
    provider_name = settings.ai_provider.strip().lower()
    if provider_name == "auto":
        if settings.environment.strip().lower() == "production":
            return AzureAIProvider()
        if settings.azure_openai_api_key:
            return AzureAIProvider()
        return MockAIProvider()
    if provider_name == "azure":
        return AzureAIProvider()
    if provider_name == "mock":
        return MockAIProvider()
    raise ValueError(f"Unsupported AI_PROVIDER '{settings.ai_provider}'.")


def create_messaging_provider(*, business_whatsapp_number: str | None):
    """Select outbound messaging provider based on environment/config."""
    provider_name = settings.messaging_provider.strip().lower()
    if provider_name == "auto":
        if settings.environment.strip().lower() == "production":
            provider_name = "whatsapp_cloud"
        else:
            provider_name = "mock"

    if provider_name == "mock":
        return MockMessagingProvider()
    if provider_name == "whatsapp_cloud":
        return WhatsAppCloudProvider(phone_number_id=business_whatsapp_number)
    raise ValueError(f"Unsupported MESSAGING_PROVIDER '{settings.messaging_provider}'.")


def _get_business_config(*, db: Session, business_id) -> BusinessConfig | None:
    query = (
        select(BusinessConfig)
        .where(BusinessConfig.business_id == business_id)
        .limit(1)
    )
    return db.execute(query).scalars().first()
