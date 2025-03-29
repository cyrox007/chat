from fastapi import Depends, FastAPI, APIRouter, status

from components.auth.middleware import auth_middle
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
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.logout
    )
    router.add_api_route(
        '/by-uids',
        methods=['POST'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_users_by_uids
    )
    router.add_api_route(
        '/{uid}',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_user_by_uid,
        dependencies=[Depends(auth_middle)]
    )
    app.include_router(router)