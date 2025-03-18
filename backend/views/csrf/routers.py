from fastapi import FastAPI, APIRouter, status

from views.csrf import handlers

def install(app: FastAPI):
    router = APIRouter(prefix="/csrf")

    router.add_api_route(
        '/get',
        methods=['GET'],
        endpoint=handlers.get_csrf
    )
    app.include_router(router)