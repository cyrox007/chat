from fastapi import FastAPI
from fastapi.testclient import TestClient

from middlewares import csrf_middleware, error_handling_middleware


def _build_app() -> FastAPI:
    app = FastAPI()
    csrf_middleware(app)
    error_handling_middleware(app)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("downstream failure")

    return app


def test_get_downstream_exception_is_not_mislabeled_as_csrf_error():
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred."}
