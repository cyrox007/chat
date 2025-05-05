from fastapi import HTTPException, Request, Response, status
from components.decorators.db import get_session
from components.room.model import Room
from uuid import UUID
from utils.logger import setup_logger  # Импортируем централизованный логгер

# Создаем логгер для этого модуля
logger = setup_logger(__name__)

@get_session
async def get_rooms(db_session=None):
    try:
        logger.info("Fetching all active rooms")
        rooms = await Room.get_all_active_rooms(db_session)
        logger.debug(f"Found {len(rooms)} active rooms")
        return {"status": "ok", "rooms": [room.__dict__ for room in rooms]}
    except Exception as e:
        logger.error(f"Error fetching rooms: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@get_session
async def create_room(request: Request, response: Response, db_session = None):
    room_data = await request.json()
    try:
        user = request.state.user  # Получаем данные пользователя из middleware
        logger.info(f"Creating new room for user {user['user_uid']}")

        new_room = await Room.create_room(db_session, room_data, owner_uid=UUID(user["user_uid"]))
        logger.info(f"Room created successfully: {new_room.uid}")
        return {"status": "ok", "room": new_room.__dict__}
    except Exception as e:
        logger.error(f"Error creating room: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": "Internal server error"}


@get_session
async def get_room(room_uid: UUID, request: Request, response: Response, db_session = None):
    try:
        user = request.state.user  # Получаем данные пользователя из middleware
        logger.info(f"Fetching room with UID: {room_uid}")

        room = await Room.get_room_with_details(db_session, room_uid)
        if not room:
            logger.warning(f"Room not found: {room_uid}")
            response.status_code = status.HTTP_404_NOT_FOUND
            return { 'status': 'error', 'message': f"Room not found: {room_uid}" }

        logger.info(f"Room fetched successfully: {room['uid']}")
        return {"status": "ok", "room": room}
    except Exception as e:
        logger.error(f"Error fetching room: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": "Internal server error"}


@get_session
async def update_room(room_uid: UUID, room_data: dict, request: Request, db_session=None):
    try:
        user = request.state.user  # Получаем данные пользователя из middleware
        logger.info(f"Updating room with UID: {room_uid}")

        room = await Room.get_room_by_uid(db_session, room_uid)
        if not room:
            logger.warning(f"Room not found: {room_uid}")
            raise HTTPException(status_code=404, detail="Room not found")

        if room.owner_uid != UUID(user["uid"]):
            logger.warning(f"User {user['uid']} is not the owner of room {room_uid}")
            raise HTTPException(status_code=403, detail="You are not the owner of this room")

        updated_room = await Room.update_room(db_session, room_uid, room_data)
        logger.info(f"Room updated successfully: {room_uid}")
        return {"status": "ok", "room": updated_room.__dict__}
    except Exception as e:
        logger.error(f"Error updating room: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@get_session
async def delete_room(room_uid: UUID, request: Request, db_session=None):
    try:
        user = request.state.user  # Получаем данные пользователя из middleware
        logger.info(f"Deleting room with UID: {room_uid}")

        room = await Room.get_room_by_uid(db_session, room_uid)
        if not room:
            logger.warning(f"Room not found: {room_uid}")
            raise HTTPException(status_code=404, detail="Room not found")

        if room.owner_uid != UUID(user["uid"]):
            logger.warning(f"User {user['uid']} is not the owner of room {room_uid}")
            raise HTTPException(status_code=403, detail="You are not the owner of this room")

        await Room.delete_room(db_session, room_uid)
        logger.info(f"Room deleted successfully: {room_uid}")
        return {"status": "ok", "message": "Room deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting room: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")