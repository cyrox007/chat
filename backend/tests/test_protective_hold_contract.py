import os
import unittest
from unittest.mock import patch

from components.moderation.automation_settings import load_moderation_automation_config
from components.moderation.protective_hold import _ALLOWED_CAPABILITIES, _SIGNAL_CAPABILITY


class ProtectiveHoldContractTests(unittest.TestCase):
    def test_automation_is_disabled_by_default_and_duration_is_bounded(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MODERATION_PROTECTIVE_HOLDS_ENABLED", None)
            config = load_moderation_automation_config()
        self.assertFalse(config.enabled)
        self.assertGreaterEqual(config.hold_minutes, 5)
        self.assertLessEqual(config.hold_minutes, 15)
        self.assertGreaterEqual(config.min_high_signals, 2)

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
