import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


BACKEND_DIR = Path(__file__).resolve().parents[1]


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


def _start_server(listener: socket.socket, log_file) -> subprocess.Popen:
    env = os.environ.copy()
    env.update(
        DEBUG="False",
        WEB_CONCURRENCY="2",
        UVICORN_FD=str(listener.fileno()),
        FORWARDED_ALLOW_IPS="127.0.0.1",
    )
    return subprocess.Popen(
        [sys.executable, "run_server.py"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
        pass_fds=(listener.fileno(),),
    )


def _stop_server(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


@unittest.skipUnless(
    os.getenv("PUBCHAT_PRODUCTION_RELOAD_INTEGRATION") == "1",
    "production reload integration is opt-in",
)
class ProductionReloadIntegrationTest(unittest.TestCase):
    def test_listener_survives_worker_reload_and_supervisor_restart(self):
        if not hasattr(signal, "SIGHUP"):
            self.skipTest("SIGHUP is not available on this platform")

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1024)
        listener.set_inheritable(True)
        port = listener.getsockname()[1]
        health_url = f"http://127.0.0.1:{port}/health/live"

        log_file = tempfile.TemporaryFile(mode="w+")
        process = _start_server(listener, log_file)

        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not _http_ok(health_url):
                if process.poll() is not None:
                    log_file.flush()
                    log_file.seek(0)
                    self.fail(f"production server exited during startup:\n{log_file.read()}")
                time.sleep(0.1)
            self.assertTrue(_http_ok(health_url), "production server never became live")

            # Routine deploy path: the Uvicorn supervisor stays alive and rolls
            # workers one by one on SIGHUP.
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

            # Crash/restart safety net: emulate systemd keeping the listening
            # socket open while the whole Uvicorn supervisor is replaced. A
            # request made while no worker exists must queue on that socket and
            # complete after the replacement process starts, rather than seeing
            # connection-refused/502 at the reverse proxy.
            _stop_server(process)
            self.assertEqual(listener.getsockname()[1], port, "persistent listener closed with the supervisor")

            queued_probe = {}

            def request_during_restart():
                queued_probe["result"] = _http_probe(health_url, timeout=8.0)

            thread = threading.Thread(target=request_during_restart, daemon=True)
            thread.start()
            time.sleep(0.25)

            process = _start_server(listener, log_file)
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive(), "request remained stuck after supervisor replacement")
            ok, elapsed, error = queued_probe.get("result", (False, 0.0, "missing probe result"))
            self.assertTrue(ok, f"persistent listener failed across supervisor restart after {elapsed:.3f}s: {error}")

            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not _http_ok(health_url):
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            self.assertTrue(_http_ok(health_url), "replacement production supervisor never became live")
        finally:
            _stop_server(process)
            listener.close()
            log_file.close()
