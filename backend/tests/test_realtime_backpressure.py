import asyncio
import time
import unittest

from socket_manager.outbound import OutboundPump


class FakeWebSocket:
    def __init__(self, *, block=False):
        self.block = block
        self.release = asyncio.Event()
        self.sent = []

    async def send_json(self, message):
        if self.block:
            await self.release.wait()
        self.sent.append(message)


class OutboundPumpTests(unittest.TestCase):
    def test_fast_consumer_preserves_order(self):
        async def run_case():
            failures = []

            async def on_failure(reason):
                failures.append(reason)

            websocket = FakeWebSocket()
            pump = OutboundPump(
                websocket,
                queue_size=8,
                send_timeout=0.2,
                on_failure=on_failure,
            )
            pump.start()
            try:
                for sequence in range(5):
                    self.assertTrue(pump.enqueue({"sequence": sequence}))
                await asyncio.wait_for(pump.queue.join(), timeout=1)
                self.assertEqual(
                    [item["sequence"] for item in websocket.sent],
                    [0, 1, 2, 3, 4],
                )
                self.assertEqual(failures, [])
            finally:
                await pump.stop()

        asyncio.run(run_case())

    def test_queue_overflow_is_non_blocking_and_isolates_slow_consumer(self):
        async def run_case():
            failure = asyncio.Event()
            reasons = []

            async def on_failure(reason):
                reasons.append(reason)
                failure.set()

            websocket = FakeWebSocket(block=True)
            pump = OutboundPump(
                websocket,
                queue_size=2,
                send_timeout=2.0,
                on_failure=on_failure,
            )
            pump.start()
            try:
                self.assertTrue(pump.enqueue({"sequence": 0}))
                await asyncio.sleep(0)  # sender takes sequence 0 and becomes blocked
                self.assertTrue(pump.enqueue({"sequence": 1}))
                self.assertTrue(pump.enqueue({"sequence": 2}))

                started = time.monotonic()
                self.assertFalse(pump.enqueue({"sequence": 3}))
                elapsed = time.monotonic() - started

                # Fan-out must not wait for the slow socket's send timeout.
                self.assertLess(elapsed, 0.05)
                await asyncio.wait_for(failure.wait(), timeout=0.2)
                self.assertEqual(reasons, ["queue_full"])
            finally:
                websocket.release.set()
                await pump.stop()

        asyncio.run(run_case())

    def test_send_timeout_evicts_stalled_consumer(self):
        async def run_case():
            failure = asyncio.Event()
            reasons = []

            async def on_failure(reason):
                reasons.append(reason)
                failure.set()

            websocket = FakeWebSocket(block=True)
            pump = OutboundPump(
                websocket,
                queue_size=4,
                send_timeout=0.05,
                on_failure=on_failure,
            )
            pump.start()
            try:
                self.assertTrue(pump.enqueue({"sequence": 1}))
                await asyncio.wait_for(failure.wait(), timeout=0.3)
                self.assertEqual(reasons, ["send_timeout"])
            finally:
                websocket.release.set()
                await pump.stop()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
