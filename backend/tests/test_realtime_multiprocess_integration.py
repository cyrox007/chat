import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from uuid import UUID

import redis.asyncio as redis
import websockets
from websockets.exceptions import ConnectionClosed

from components.realtime.service import RealtimeService
from settings import config


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _allocate_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _spawn_uvicorn(port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["DEBUG"] = "False"
    env["REDIS_URL"] = config.REDIS_URL
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--workers",
            "1",
            "--timeout-graceful-shutdown",
            "3",
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _wait_for_server(process, port)
    return process


def _wait_for_server(process: subprocess.Popen, port: int, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise AssertionError(
                f"Uvicorn process exited before becoming ready on port {port}:\n{output}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)

    _stop_process(process)
    raise AssertionError(f"Uvicorn process did not become ready on port {port}")


def _stop_process(process: subprocess.Popen | None) -> str:
    if process is None:
        return ""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    return process.stdout.read() if process.stdout else ""


@unittest.skipUnless(
    os.getenv("PUBCHAT_REALTIME_MULTIPROCESS_INTEGRATION") == "1",
    "Realtime multi-process integration environment is not enabled",
)
class RealtimeMultiprocessIntegrationTests(unittest.TestCase):
    def test_real_uvicorn_workers_and_rolling_restart(self):
        async def run_case():
            original_debug = config.DEBUG
            service = RealtimeService()
            admin = redis.from_url(config.REDIS_URL, decode_responses=True)
            server_a = None
            server_b = None
            socket_a = None
            socket_b = None

            account_a = UUID("00000000-0000-0000-0000-000000000611")
            account_b = UUID("00000000-0000-0000-0000-000000000612")
            port_a = _allocate_port()
            port_b = _allocate_port()

            async def connect(port: int, account_uid: UUID):
                ticket, _ = await service.issue_ticket(account_uid, "messenger")
                websocket = await websockets.connect(
                    f"ws://127.0.0.1:{port}/ws/v2/messenger",
                    ping_interval=None,
                    open_timeout=5,
                    close_timeout=2,
                )
                await websocket.send(json.dumps({"type": "auth", "ticket": ticket}))
                ready = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))
                self.assertEqual(ready["type"], "realtime_ready")
                self.assertEqual(ready["protocol"], 2)
                self.assertEqual(ready["target"], "messenger")
                return websocket

            async def receive_type(websocket, expected_type: str, timeout: float = 5.0):
                deadline = asyncio.get_running_loop().time() + timeout
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        self.fail(f"Did not receive realtime frame type {expected_type!r}")
                    frame = json.loads(await asyncio.wait_for(websocket.recv(), timeout=remaining))
                    if frame.get("type") == expected_type:
                        return frame

            async def wait_online(account_uid: UUID, timeout: float = 5.0):
                deadline = asyncio.get_running_loop().time() + timeout
                while asyncio.get_running_loop().time() < deadline:
                    if await service.is_online(account_uid):
                        return
                    await asyncio.sleep(0.1)
                self.fail(f"Distributed presence did not become visible for {account_uid}")

            try:
                config.DEBUG = False
                await admin.flushdb()
                await service.start()
                self.assertTrue(service.distributed)

                server_a = _spawn_uvicorn(port_a)
                server_b = _spawn_uvicorn(port_b)

                # Each socket is owned by a different OS process. One-time tickets
                # are issued in this test process and consumed by those workers.
                socket_a = await connect(port_a, account_a)
                socket_b = await connect(port_b, account_b)
                await wait_online(account_a)
                await wait_online(account_b)

                # A third process publishes through Redis. Each worker must fan the
                # event out only to its process-local WebSocket object.
                await service.publish_user(
                    account_a,
                    {"type": "multiprocess_probe", "worker": "a", "sequence": 1},
                )
                frame_a = await receive_type(socket_a, "multiprocess_probe")
                self.assertEqual(frame_a["worker"], "a")
                self.assertEqual(frame_a["sequence"], 1)

                await service.publish_user(
                    account_b,
                    {"type": "multiprocess_probe", "worker": "b", "sequence": 1},
                )
                frame_b = await receive_type(socket_b, "multiprocess_probe")
                self.assertEqual(frame_b["worker"], "b")
                self.assertEqual(frame_b["sequence"], 1)

                # Simulate one node in a rolling restart. The other node must keep
                # serving traffic while the client reconnects with a fresh ticket.
                await asyncio.to_thread(_stop_process, server_a)
                server_a = None
                with self.assertRaises(ConnectionClosed):
                    while True:
                        await asyncio.wait_for(socket_a.recv(), timeout=5)
                socket_a = None

                await service.publish_user(
                    account_b,
                    {"type": "rolling_restart_probe", "sequence": 2},
                )
                frame_b = await receive_type(socket_b, "rolling_restart_probe")
                self.assertEqual(frame_b["sequence"], 2)

                server_a = _spawn_uvicorn(port_a)
                socket_a = await connect(port_a, account_a)
                await wait_online(account_a)

                await service.publish_user(
                    account_a,
                    {"type": "rolling_restart_probe", "sequence": 3},
                )
                frame_a = await receive_type(socket_a, "rolling_restart_probe")
                self.assertEqual(frame_a["sequence"], 3)
            finally:
                if socket_a is not None:
                    await socket_a.close()
                if socket_b is not None:
                    await socket_b.close()
                await asyncio.to_thread(_stop_process, server_a)
                await asyncio.to_thread(_stop_process, server_b)
                config.DEBUG = original_debug
                await service.stop()
                try:
                    await admin.flushdb()
                finally:
                    await admin.aclose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
