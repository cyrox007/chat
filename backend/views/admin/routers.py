from fastapi import Depends, FastAPI, APIRouter, status

from components.auth.middleware import auth_middle
from views.admin import handlers


def install(app: FastAPI):
    router = APIRouter(prefix='/admin')

    router.add_api_route(
        '/penalties/assign',
        methods=['POST'],
        status_code=status.HTTP_201_CREATED,
        endpoint=handlers.assign_penalty,
        dependencies=[Depends(auth_middle)]
    )

    app.include_router(router)