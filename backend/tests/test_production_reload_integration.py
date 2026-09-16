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


def _http_probe(url: str, timeout: float = 3.0) -> tuple[bool, float, str | None]:
    started = time.monotonic()
    try:
        with urlopen(url, timeout=timeout) as response:
            elapsed = time.monotonic() - started
            return response.status == 200, elapsed, None
    except (OSError, URLError) as exc:
        elapsed = time.monotonic() - started
        return False, elapsed, repr(exc)


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    return _http_probe(url, timeout=timeout)[0]


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

            failures = []
            latencies = []
            checks = 0
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                checks += 1
                ok, elapsed, error = _http_probe(health_url)
                latencies.append(elapsed)
                if not ok:
                    failures.append((elapsed, error))
                time.sleep(0.05)

            self.assertIsNone(process.poll(), "Uvicorn supervisor exited after SIGHUP")
            self.assertGreater(checks, 10)
            self.assertEqual(
                failures,
                [],
                f"HTTP request failed during rolling worker reload: {failures}; max_latency={max(latencies):.3f}s",
            )
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            if process.stdout:
                process.stdout.close()
