import os
import signal
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _http_ok(url: str, timeout: float = 1.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


@unittest.skipUnless(
    os.getenv("PUBCHAT_PRODUCTION_RELOAD_INTEGRATION") == "1",
    "production reload integration is opt-in",
)
class ProductionReloadIntegrationTest(unittest.TestCase):
    def test_sighup_rolls_workers_without_dropping_http(self):
        if not hasattr(signal, "SIGHUP"):
            self.skipTest("SIGHUP is not available on this platform")

        port = _free_port()
        env = os.environ.copy()
        env.update(
            DEBUG="False",
            PORT=str(port),
            WEB_CONCURRENCY="2",
            FORWARDED_ALLOW_IPS="127.0.0.1",
        )
        process = subprocess.Popen(
            [sys.executable, "run_server.py"],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        health_url = f"http://127.0.0.1:{port}/health/live"

        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not _http_ok(health_url):
                if process.poll() is not None:
                    output = process.stdout.read() if process.stdout else ""
                    self.fail(f"production server exited during startup:\n{output}")
                time.sleep(0.1)
            self.assertTrue(_http_ok(health_url), "production server never became live")

            os.kill(process.pid, signal.SIGHUP)

            failures = 0
            checks = 0
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                checks += 1
                if not _http_ok(health_url):
                    failures += 1
                time.sleep(0.05)

            self.assertIsNone(process.poll(), "Uvicorn supervisor exited after SIGHUP")
            self.assertGreater(checks, 20)
            self.assertEqual(failures, 0, "HTTP became unavailable during rolling worker reload")
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
