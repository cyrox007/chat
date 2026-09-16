from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Optional

from fastapi import WebSocket

FailureCallback = Callable[[str], Awaitable[None]]


class OutboundPump:
    """Serialize one socket's outbound frames without blocking global fan-out.

    Redis/pub-sub callbacks only enqueue frames. A dedicated task performs the
    potentially slow socket writes. Once the bounded queue is full, or one send
    exceeds the configured timeout, the owner is notified so that only this
    consumer can be disconnected.
    """

    def __init__(
        self,
        websocket: WebSocket,
        *,
        queue_size: int,
        send_timeout: float,
        on_failure: FailureCallback,
    ) -> None:
        self.websocket = websocket
        self.queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=max(1, queue_size))
        self.send_timeout = max(0.01, send_timeout)
        self.on_failure = on_failure
        self._task: Optional[asyncio.Task] = None
        self._failure_task: Optional[asyncio.Task] = None

    @property
    def pending(self) -> int:
        return self.queue.qsize()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.running:
            return
        self._task = asyncio.create_task(self._run(), name="pubchat-websocket-outbound")

    def enqueue(self, message: dict) -> bool:
        if not self.running:
            self._schedule_failure("sender_not_running")
            return False
        try:
            self.queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            self._schedule_failure("queue_full")
            return False

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def _schedule_failure(self, reason: str) -> None:
        if self._failure_task and not self._failure_task.done():
            return
        self._failure_task = asyncio.create_task(
            self.on_failure(reason),
            name="pubchat-websocket-outbound-failure",
        )

    async def _run(self) -> None:
        while True:
            try:
                message = await self.queue.get()
            except asyncio.CancelledError:
                raise

            try:
                await asyncio.wait_for(
                    self.websocket.send_json(message),
                    timeout=self.send_timeout,
                )
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                self._schedule_failure("send_timeout")
                return
            except Exception:
                self._schedule_failure("send_error")
                return
            finally:
                self.queue.task_done()
