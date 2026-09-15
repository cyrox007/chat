import asyncio
import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from components.notification import worker_service
from components.notification.model import NotificationWorkerState


class _FakeSession:
    def __init__(self):
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        self.commits += 1


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

    def test_worker_pages_with_durable_cursor_and_aggregates_stats(self):
        first = UUID('00000000-0000-0000-0000-000000000001')
        second = UUID('00000000-0000-0000-0000-000000000002')
        third = UUID('00000000-0000-0000-0000-000000000003')
        state = SimpleNamespace(cursor_account_uid=None, updated_at=None)

        lock = AsyncMock(return_value=state)
        page = AsyncMock(side_effect=[[first, second], [third]])
        reconcile = AsyncMock(side_effect=[(2, 0), (0, 1)])

        async def run_case():
            with patch.object(worker_service, 'lock_worker_state', lock), patch.object(
                worker_service,
                'reminder_account_page',
                page,
            ), patch.object(
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
        self.assertTrue(stats.acquired)
        self.assertTrue(stats.wrapped)
        self.assertEqual(stats.batches, 2)
        self.assertEqual(stats.accounts_seen, 3)
        self.assertEqual(stats.accounts_synced, 2)
        self.assertEqual(stats.accounts_failed, 1)
        self.assertIsNone(state.cursor_account_uid)

        self.assertIsNone(page.await_args_list[0].kwargs['after_uid'])
        self.assertEqual(page.await_args_list[1].kwargs['after_uid'], second)

    def test_worker_resumes_from_saved_cursor_when_batch_budget_ends(self):
        saved = UUID('00000000-0000-0000-0000-000000000010')
        next_one = UUID('00000000-0000-0000-0000-000000000011')
        next_two = UUID('00000000-0000-0000-0000-000000000012')
        state = SimpleNamespace(cursor_account_uid=saved, updated_at=None)
        lock = AsyncMock(return_value=state)
        page = AsyncMock(return_value=[next_one, next_two])
        reconcile = AsyncMock(return_value=(2, 0))

        async def run_case():
            with patch.object(worker_service, 'lock_worker_state', lock), patch.object(
                worker_service,
                'reminder_account_page',
                page,
            ), patch.object(
                worker_service,
                'reconcile_reminder_accounts',
                reconcile,
            ):
                return await worker_service.run_reminder_worker(
                    _FakeSessionFactory(),
                    batch_size=2,
                    max_batches=1,
                )

        stats = asyncio.run(run_case())
        self.assertTrue(stats.acquired)
        self.assertFalse(stats.wrapped)
        self.assertEqual(page.await_args.kwargs['after_uid'], saved)
        self.assertEqual(state.cursor_account_uid, next_two)

    def test_overlapping_worker_skips_when_cursor_row_is_locked(self):
        async def run_case():
            with patch.object(worker_service, 'lock_worker_state', AsyncMock(return_value=None)):
                return await worker_service.run_reminder_worker(_FakeSessionFactory())

        stats = asyncio.run(run_case())
        self.assertFalse(stats.acquired)
        self.assertEqual(stats.accounts_seen, 0)

    def test_worker_state_model_and_migration_exist(self):
        self.assertEqual(NotificationWorkerState.__tablename__, 'notification_worker_state')
        migration = Path('alembic/versions/k0a6d4f88003_notification_worker_cursor.py').read_text(encoding='utf-8')
        self.assertIn('notification_worker_state', migration)
        self.assertIn('k0a6d4f88002', migration)
        self.assertIn(worker_service.WORKER_NAME_ACTIVITY_REMINDERS, migration)

    def test_worker_service_has_no_web_or_scheduler_loop(self):
        source = inspect.getsource(worker_service)
        self.assertIn('with_for_update(skip_locked=True)', source)
        self.assertNotIn('asyncio.create_task', source)
        self.assertNotIn('while True', source)


if __name__ == '__main__':
    unittest.main()
