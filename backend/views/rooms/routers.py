from fastapi import FastAPI, APIRouter, WebSocket, status, Depends

from components.auth.middleware import auth_middle
from views.rooms import handlers

def install(app: FastAPI):
    router = APIRouter(prefix='/rooms')

    # Получение списка комнат
    router.add_api_route(
        '/',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_rooms,
        dependencies=[Depends(auth_middle)]
    )

    # Создание комнаты
    router.add_api_route(
        '/',
        methods=['POST'],
        status_code=status.HTTP_201_CREATED,
        endpoint=handlers.create_room,
        dependencies=[Depends(auth_middle)]
    )

    # Обновление комнаты
    router.add_api_route(
        '/{room_uid}',
        methods=['GET'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_room,
        dependencies=[Depends(auth_middle)]
    )
    # Обновление комнаты
    router.add_api_route(
        '/{room_uid}',
        methods=['PUT'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.update_room,
        dependencies=[Depends(auth_middle)]
    )

    # Удаление комнаты
    router.add_api_route(
        '/{room_uid}',
        methods=['DELETE'],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.delete_room,
        dependencies=[Depends(auth_middle)]
    )

    app.include_router(router)
