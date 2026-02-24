"""Core bot orchestration service."""

from app.interfaces.ai_provider import AIProvider
from app.interfaces.messaging_provider import MessagingProvider
from app.services.flow_manager import FlowManager
from app.services.intent_engine import IntentEngine


class BotService:
    """Coordinates intent detection, state flow, and response delivery."""

    def __init__(
        self,
        ai_provider: AIProvider,
        messaging_provider: MessagingProvider,
        intent_engine: IntentEngine,
        flow_manager: FlowManager,
    ) -> None:
        self.ai_provider = ai_provider
        self.messaging_provider = messaging_provider
        self.intent_engine = intent_engine
        self.flow_manager = flow_manager

    async def handle_message(self, user: str, message: str) -> dict[str, str]:
        """Route one inbound message through intent + conversation flow."""
        intent = self.intent_engine.detect_intent(message=message)
        flow_response = await self.flow_manager.handle(intent=intent, user=user, message=message)

        if flow_response is None:
            # Fallback path that will later be replaced by a real AI provider.
            current_state = self.flow_manager.conversation_manager.get_state(user=user)
            context = {
                "user": user,
                "state": current_state,
                "intent": intent,
                "mode": self.flow_manager.mode,
            }
            response = await self.ai_provider.generate_response(message=message, context=context)
        else:
            response = flow_response

        await self.messaging_provider.send_message(user=user, message=response)
        return {
            "user": user,
            "response": response,
        }

