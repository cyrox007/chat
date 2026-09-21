import os
import unittest
from unittest.mock import patch

from components.moderation.automation_settings import automation_mode, load_moderation_automation_config
from components.moderation.protective_hold import _ALLOWED_CAPABILITIES, _SIGNAL_CAPABILITY


class ProtectiveHoldContractTests(unittest.TestCase):
    def test_automation_is_disabled_by_default_and_duration_is_bounded(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MODERATION_PROTECTIVE_HOLDS_ENABLED", None)
            config = load_moderation_automation_config()
        self.assertFalse(config.enabled)
        self.assertEqual(automation_mode(config), "off")
        self.assertGreaterEqual(config.hold_minutes, 5)
        self.assertLessEqual(config.hold_minutes, 15)
        self.assertGreaterEqual(config.min_high_signals, 2)

    def test_shadow_mode_never_counts_as_enabled_enforcement(self):
        with patch.dict(
            os.environ,
            {
                "MODERATION_PROTECTIVE_HOLDS_MODE": "shadow",
                "MODERATION_PROTECTIVE_HOLDS_ENABLED": "false",
            },
            clear=False,
        ):
            config = load_moderation_automation_config()
        self.assertFalse(config.enabled)
        self.assertEqual(automation_mode(config), "shadow")
        self.assertFalse(config.calibration_gate_required)

    def test_enforce_mode_is_calibration_gated_and_requires_approval(self):
        with patch.dict(
            os.environ,
            {
                "MODERATION_PROTECTIVE_HOLDS_MODE": "enforce",
                "MODERATION_PROTECTIVE_HOLD_ENFORCEMENT_APPROVED": "false",
            },
            clear=False,
        ):
            config = load_moderation_automation_config()
        self.assertTrue(config.enabled)
        self.assertEqual(automation_mode(config), "enforce")
        self.assertTrue(config.calibration_gate_required)
        self.assertFalse(config.enforcement_approved)
        self.assertGreaterEqual(config.calibration_min_labels_per_type, 5)
        self.assertLessEqual(
            config.calibration_max_false_positive_percent,
            50.0,
        )

    def test_legacy_enabled_alias_cannot_bypass_calibration_gate(self):
        with patch.dict(
            os.environ,
            {
                "MODERATION_PROTECTIVE_HOLDS_ENABLED": "true",
            },
            clear=False,
        ):
            os.environ.pop("MODERATION_PROTECTIVE_HOLDS_MODE", None)
            os.environ.pop(
                "MODERATION_PROTECTIVE_HOLD_ENFORCEMENT_APPROVED", None
            )
            config = load_moderation_automation_config()
        self.assertEqual(automation_mode(config), "enforce")
        self.assertTrue(config.calibration_gate_required)
        self.assertFalse(config.enforcement_approved)

    def test_only_low_risk_capabilities_are_automatable(self):
        self.assertEqual(
            _ALLOWED_CAPABILITIES,
            frozenset({"messenger.send", "invitation.send"}),
        )
        self.assertNotIn("account.access", _ALLOWED_CAPABILITIES)
        self.assertNotIn("media.upload", _ALLOWED_CAPABILITIES)
        self.assertNotIn("space.chat.send", _ALLOWED_CAPABILITIES)
        self.assertEqual(
            set(_SIGNAL_CAPABILITY),
            {"dm_distinct_recipient_burst", "space_invite_recipient_burst"},
        )


if __name__ == "__main__":
    unittest.main()
