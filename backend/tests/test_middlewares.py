import asyncio
import json
import unittest

from fastapi import FastAPI

from middlewares import csrf_middleware, error_handling_middleware


def _build_app() -> FastAPI:
    app = FastAPI()
    csrf_middleware(app)
    error_handling_middleware(app)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("downstream failure")

    return app


async def _get(app: FastAPI, path: str) -> tuple[int, dict]:
    messages: list[dict] = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }

    await app(scope, receive, send)
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return status, json.loads(body)


class MiddlewareTests(unittest.TestCase):
    def test_get_downstream_exception_is_not_mislabeled_as_csrf_error(self):
        status, payload = asyncio.run(_get(_build_app(), "/boom"))

        self.assertEqual(status, 500)
        self.assertEqual(payload, {"detail": "An unexpected error occurred."})


if __name__ == "__main__":
    unittest.main()
