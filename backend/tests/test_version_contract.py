import unittest

from app import app
from utils.version import PROJECT_VERSION, PROJECT_VERSION_INFO, parse_project_version


class VersionContractTests(unittest.TestCase):
    def test_current_version_is_valid_semver_channel(self):
        self.assertTrue(PROJECT_VERSION_INFO["valid"])
        self.assertEqual(PROJECT_VERSION_INFO["version"], PROJECT_VERSION)
        self.assertIn(PROJECT_VERSION_INFO["channel"], {"alpha", "beta", "stable"})

    def test_fastapi_exposes_same_project_version(self):
        self.assertEqual(app.version, PROJECT_VERSION)

    def test_stable_version_has_no_prerelease_suffix(self):
        info = parse_project_version("1.0.0")
        self.assertTrue(info["valid"])
        self.assertEqual(info["channel"], "stable")
        self.assertIsNone(info["iteration"])

    def test_unknown_channels_are_rejected(self):
        self.assertFalse(parse_project_version("0.3.0-rc.1")["valid"])


if __name__ == "__main__":
    unittest.main()
