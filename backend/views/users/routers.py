from fastapi import FastAPI, APIRouter, status

from views.users import handlers

def install(app: FastAPI):
    router = APIRouter(prefix='/users')

    router.add_api_route(
        '/register',
        methods=['POST'],
        status_code=status.HTTP_201_CREATED,
        endpoint=handlers.register
    )
    router.add_api_route(
        '/login',
        methods=['POST'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.login
    )
    router.add_api_route(
        '/logout',
        methods=['POST'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.logout
    )
    app.include_router(router)