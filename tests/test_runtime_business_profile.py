"""Unit tests for runtime profile normalization from BusinessConfig."""

from __future__ import annotations

import unittest
from uuid import uuid4

from app.models.business import BusinessConfig
from app.services.runtime_business_profile import RuntimeBusinessProfile


class RuntimeBusinessProfileTestCase(unittest.TestCase):
    """Covers defaults and normalization rules for runtime profile creation."""

    def test_defaults_without_business_config(self) -> None:
        profile = RuntimeBusinessProfile.from_business_config(business_config=None)
        self.assertEqual(profile.mode, RuntimeBusinessProfile.ASSISTED_MODE)
        self.assertTrue(profile.handoff_enabled)
        self.assertEqual(profile.tone, RuntimeBusinessProfile.CERCANO_TONE)

    def test_uses_mode_specific_tone_for_assisted(self) -> None:
        business_config = BusinessConfig(
            business_id=uuid4(),
            mode="assisted",
            handoff_enabled=False,
            assisted_config={"tone": "formal"},
            autonomous_config={"tone": "cercano"},
        )

        profile = RuntimeBusinessProfile.from_business_config(business_config=business_config)

        self.assertEqual(profile.mode, RuntimeBusinessProfile.ASSISTED_MODE)
        self.assertFalse(profile.handoff_enabled)
        self.assertEqual(profile.tone, RuntimeBusinessProfile.FORMAL_TONE)

    def test_uses_mode_specific_tone_for_autonomous(self) -> None:
        business_config = BusinessConfig(
            business_id=uuid4(),
            mode="autonomous",
            handoff_enabled=True,
            assisted_config={"tone": "cercano"},
            autonomous_config={"tone": "formal"},
        )

        profile = RuntimeBusinessProfile.from_business_config(business_config=business_config)

        self.assertEqual(profile.mode, RuntimeBusinessProfile.AUTONOMOUS_MODE)
        self.assertTrue(profile.handoff_enabled)
        self.assertEqual(profile.tone, RuntimeBusinessProfile.FORMAL_TONE)

    def test_invalid_values_fallback_to_safe_defaults(self) -> None:
        business_config = BusinessConfig(
            business_id=uuid4(),
            mode="legacy-mode",
            handoff_enabled=True,
            assisted_config={"tone": "invalid-tone"},
            autonomous_config={},
        )

        profile = RuntimeBusinessProfile.from_business_config(business_config=business_config)

        self.assertEqual(profile.mode, RuntimeBusinessProfile.ASSISTED_MODE)
        self.assertEqual(profile.tone, RuntimeBusinessProfile.CERCANO_TONE)


if __name__ == "__main__":
    unittest.main()
