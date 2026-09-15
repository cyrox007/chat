import asyncio
import inspect
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

from components.notification import worker_service


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSessionFactory:
    def __call__(self):
        return _FakeSession()


class NotificationWorkerContractTests(unittest.TestCase):
    def test_worker_is_not_started_from_fastapi_lifespan(self):
        source = Path('app.py').read_text(encoding='utf-8')
        self.assertNotIn('notification_reconciler', source)
        self.assertNotIn('run_reminder_worker', source)

    def test_worker_defaults_are_bounded(self):
        self.assertGreater(worker_service.DEFAULT_WORKER_BATCH_SIZE, 0)
        self.assertLessEqual(
            worker_service.DEFAULT_WORKER_BATCH_SIZE,
            worker_service.MAX_WORKER_BATCH_SIZE,
        )
        self.assertGreater(worker_service.DEFAULT_MAX_BATCHES, 0)
        self.assertLessEqual(
            worker_service.DEFAULT_MAX_BATCHES,
            worker_service.MAX_WORKER_BATCHES,
        )

    def test_worker_pages_with_cursor_and_aggregates_stats(self):
        first = UUID('00000000-0000-0000-0000-000000000001')
        second = UUID('00000000-0000-0000-0000-000000000002')
        third = UUID('00000000-0000-0000-0000-000000000003')

        page = AsyncMock(side_effect=[[first, second], [third]])
        reconcile = AsyncMock(side_effect=[(2, 0), (0, 1)])

        async def run_case():
            with patch.object(worker_service, 'reminder_account_page', page), patch.object(
                worker_service,
                'reconcile_reminder_accounts',
                reconcile,
            ):
                return await worker_service.run_reminder_worker(
                    _FakeSessionFactory(),
                    batch_size=2,
                    max_batches=5,
                )

        stats = asyncio.run(run_case())
        self.assertEqual(stats.batches, 2)
        self.assertEqual(stats.accounts_seen, 3)
        self.assertEqual(stats.accounts_synced, 2)
        self.assertEqual(stats.accounts_failed, 1)

        self.assertIsNone(page.await_args_list[0].kwargs['after_uid'])
        self.assertEqual(page.await_args_list[1].kwargs['after_uid'], second)

    def test_worker_service_has_no_web_or_scheduler_loop(self):
        source = inspect.getsource(worker_service)
        self.assertNotIn('asyncio.create_task', source)
        self.assertNotIn('while True', source)


if __name__ == '__main__':
    unittest.main()
