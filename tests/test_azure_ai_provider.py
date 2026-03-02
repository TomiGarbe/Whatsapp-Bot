"""Unit tests for AzureAIProvider message construction with runtime context."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.providers.ai.azure_ai import AzureAIProvider
from app.services.runtime_ai_context import RuntimeAIContext
from app.services.runtime_business_profile import RuntimeBusinessProfile


class _FakeCompletions:
    def __init__(self) -> None:
        self.last_payload: dict[str, object] | None = None

    def create(self, *, model: str | None, messages: list[dict[str, str]], temperature: float):
        self.last_payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="respuesta simulada"),
                )
            ]
        )


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


class AzureAIProviderTestCase(unittest.IsolatedAsyncioTestCase):
    """Verifies provider uses RuntimeAIContext for system prompt."""

    def _build_context(self) -> RuntimeAIContext:
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.AUTONOMOUS_MODE,
            handoff_enabled=True,
            tone=RuntimeBusinessProfile.FORMAL_TONE,
        )
        business = SimpleNamespace(name="JD Media", industry="marketing digital")
        return RuntimeAIContext.from_business(business=business, profile=profile)

    async def test_generate_response_uses_runtime_context_system_prompt(self) -> None:
        fake_client = _FakeClient()
        context = self._build_context()
        provider = AzureAIProvider(
            context=context,
            client=fake_client,
            deployment="gpt-test",
        )

        response = await provider.generate_response("Hola", context={"foo": "bar"})

        self.assertEqual(response, "respuesta simulada")
        payload = fake_client.chat.completions.last_payload
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["model"], "gpt-test")
        self.assertEqual(payload["temperature"], 0.7)
        messages = payload["messages"]
        self.assertIsInstance(messages, list)
        assert isinstance(messages, list)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], context.build_system_prompt())
        self.assertEqual(messages[1], {"role": "user", "content": "Hola"})


if __name__ == "__main__":
    unittest.main()
