import unittest

from settings import Config


class ModerationStorageLifecycleContractTests(unittest.TestCase):
    def _config(self) -> Config:
        config = Config()
        config.MODERATION_MEDIA_REMOVED_RETENTION_DAYS = 90
        config.MODERATION_MEDIA_BACKUP_RETENTION_DAYS = None
        config.MODERATION_MEDIA_SNAPSHOT_RETENTION_DAYS = None
        return config

    def test_production_preflight_requires_declared_backup_and_snapshot_lifecycle(self):
        config = self._config()
        with self.assertRaises(RuntimeError):
            config.ensure_moderation_media_retention_settings(
                require_storage_lifecycle=True
            )

    def test_backup_and_snapshot_may_not_outlive_private_evidence_policy(self):
        config = self._config()
        config.MODERATION_MEDIA_BACKUP_RETENTION_DAYS = 120
        config.MODERATION_MEDIA_SNAPSHOT_RETENTION_DAYS = 30
        with self.assertRaises(RuntimeError):
            config.ensure_moderation_media_retention_settings()

        config.MODERATION_MEDIA_BACKUP_RETENTION_DAYS = 30
        config.MODERATION_MEDIA_SNAPSHOT_RETENTION_DAYS = 120
        with self.assertRaises(RuntimeError):
            config.ensure_moderation_media_retention_settings()

    def test_aligned_declared_lifecycle_passes(self):
        config = self._config()
        config.MODERATION_MEDIA_BACKUP_RETENTION_DAYS = 90
        config.MODERATION_MEDIA_SNAPSHOT_RETENTION_DAYS = 30
        config.ensure_moderation_media_retention_settings(
            require_storage_lifecycle=True
        )
        status = config.moderation_media_storage_lifecycle_status()
        self.assertTrue(status["declared"])
        self.assertTrue(status["aligned"])


if __name__ == "__main__":
    unittest.main()
