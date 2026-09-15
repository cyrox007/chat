import unittest
from uuid import uuid4

from pydantic import ValidationError

from app import app
from components.realtime.schemas import RealtimeAuthFrame, RealtimeTicketRequest
from components.realtime.service import RealtimeService
from settings import config


class RealtimeContractTests(unittest.TestCase):
    def test_v2_routes_have_no_credentials_in_url(self):
        paths = {route.path for route in app.routes}
        self.assertIn('/realtime/v2/tickets', paths)
        self.assertIn('/ws/v2/rooms/{room_uid}', paths)
        self.assertIn('/ws/v2/messenger', paths)
        self.assertFalse(any('{token}' in path for path in paths))

    def test_room_ticket_requires_room_uid(self):
        with self.assertRaises(ValidationError):
            RealtimeTicketRequest(target='room')

    def test_messenger_ticket_rejects_room_uid(self):
        with self.assertRaises(ValidationError):
            RealtimeTicketRequest(target='messenger', room_uid=uuid4())

    def test_auth_frame_does_not_accept_bearer_shape(self):
        with self.assertRaises(ValidationError):
            RealtimeAuthFrame(type='auth', ticket='short')


class RealtimeTicketLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_debug_ticket_is_one_time_and_scoped(self):
        previous_debug = config.DEBUG
        config.DEBUG = True
        service = RealtimeService()
        account_uid = uuid4()
        room_uid = uuid4()
        try:
            ticket, ttl = await service.issue_ticket(account_uid, 'room', room_uid)
            self.assertGreaterEqual(ttl, 1)

            payload = await service.consume_ticket(ticket, 'room', room_uid)
            self.assertIsNotNone(payload)
            self.assertEqual(payload['account_uid'], str(account_uid))

            replay = await service.consume_ticket(ticket, 'room', room_uid)
            self.assertIsNone(replay)
        finally:
            config.DEBUG = previous_debug

    async def test_ticket_cannot_be_reused_for_another_target(self):
        previous_debug = config.DEBUG
        config.DEBUG = True
        service = RealtimeService()
        try:
            ticket, _ = await service.issue_ticket(uuid4(), 'messenger')
            invalid_scope = await service.consume_ticket(ticket, 'room', uuid4())
            self.assertIsNone(invalid_scope)
            # Scope mismatch still consumes the ticket, preventing probing/replay.
            self.assertIsNone(await service.consume_ticket(ticket, 'messenger'))
        finally:
            config.DEBUG = previous_debug


if __name__ == '__main__':
    unittest.main()
