from fastapi import APIRouter, FastAPI, status

from utils.version import PROJECT_VERSION_INFO
from views.service import handlers, health


def install(app: FastAPI):
    router = APIRouter()

    router.add_api_route(
        '/health',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_server
    )
    router.add_api_route(
        '/health/live',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=health.liveness,
    )
    router.add_api_route(
        '/health/ready',
        methods=['GET'],
        endpoint=health.readiness,
    )
    router.add_api_route(
        '/refresh',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.refresh_tokens
    )
    router.add_api_route(
        '/service/check-token',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.check_token
    )

    @router.get('/service/version', status_code=status.HTTP_200_OK)
    async def project_version():
        return {"status": "ok", **PROJECT_VERSION_INFO}

    app.include_router(router)
