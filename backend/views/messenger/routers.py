from fastapi import APIRouter, Depends, FastAPI

from components.auth.middleware import auth_middle
from views.messenger import handlers


def install(app: FastAPI):
    router = APIRouter(prefix='/messenger')

    # Только GET endpoints для начальной загрузки данных
    router.add_api_route(
        '/dialogs',
        methods=['GET'],
        endpoint=handlers.get_dialogs,
        dependencies=[Depends(auth_middle)]
    )

    """ router.add_api_route(
        '/conversation/{user_id}',
        methods=['GET'],
        endpoint=handlers.get_conversation,
        dependencies=[Depends(auth_middle)]
    ) """

    app.include_router(router)