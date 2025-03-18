from fastapi import FastAPI, APIRouter, status

from views.health import handlers

def install(app: FastAPI):
    router = APIRouter()

    router.add_api_route(
        '/health',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_server
    )
    app.include_router(router)