"""Unit tests for RuntimeAIContext prompt composition."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.services.runtime_ai_context import RuntimeAIContext
from app.services.runtime_business_profile import RuntimeBusinessProfile


class RuntimeAIContextTestCase(unittest.TestCase):
    """Validates tone/mode prompt behavior for runtime AI context."""

    def test_build_system_prompt_for_cercano_assisted(self) -> None:
        business = SimpleNamespace(name="JD Media", industry="marketing digital")
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.ASSISTED_MODE,
            handoff_enabled=True,
            tone=RuntimeBusinessProfile.CERCANO_TONE,
        )

        context = RuntimeAIContext.from_business(business=business, profile=profile)
        prompt = context.build_system_prompt()

        self.assertIn("JD Media", prompt)
        self.assertIn("marketing digital", prompt)
        self.assertIn("Tono: cercano", prompt)
        self.assertIn("Modo assisted", prompt)
        self.assertIn("No inventes informacion", prompt)
        self.assertIn("No prometas resultados garantizados", prompt)

    def test_build_system_prompt_for_formal_autonomous(self) -> None:
        business = SimpleNamespace(name="Clinica Norte", industry="salud")
        profile = RuntimeBusinessProfile(
            mode=RuntimeBusinessProfile.AUTONOMOUS_MODE,
            handoff_enabled=False,
            tone=RuntimeBusinessProfile.FORMAL_TONE,
        )

        context = RuntimeAIContext.from_business(business=business, profile=profile)
        prompt = context.build_system_prompt()

        self.assertIn("Clinica Norte", prompt)
        self.assertIn("Tono: formal", prompt)
        self.assertIn("Modo autonomous", prompt)
        self.assertIn("trato de usted", prompt)
        self.assertIn("orienta la conversacion al siguiente paso comercial", prompt)


if __name__ == "__main__":
    unittest.main()
