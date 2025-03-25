from fastapi import HTTPException, Request
from components.decorators.db import get_session
from components.room.model import Room
from uuid import UUID

@get_session
async def get_rooms(db_session = None):
    rooms = Room.get_all_active_rooms(db_session)
    return {"status": "ok", "rooms": [room.__dict__ for room in rooms]}


@get_session
async def create_room(room_data: dict, request: Request, db_session = None):
    user = request.state.user  # Получаем данные пользователя из middleware
    
    new_room = Room.create_room(db_session, room_data, owner_uid=UUID(user["user_uid"]))
    return {"status": "ok", "room": new_room.__dict__}


@get_session
async def get_room(room_uid: UUID, request: Request, db_session=None):
    user = request.state.user  # Получаем данные пользователя из middleware

    room = Room.get_room_by_uid(db_session, room_uid)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    """ if room.owner_uid != UUID(user["uid"]):
        raise HTTPException(status_code=403, detail="You are not the owner of this room") """

    #updated_room = Room.update_room(db_session, room_uid, room_data)
    return {"status": "ok", "room": room.__dict__}

@get_session
def update_room(room_uid: UUID, room_data: dict, request: Request, db_session):
    user = request.state.user  # Получаем данные пользователя из middleware

    room = Room.get_room_by_uid(db_session, room_uid)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.owner_uid != UUID(user["uid"]):
        raise HTTPException(status_code=403, detail="You are not the owner of this room")

    updated_room = Room.update_room(db_session, room_uid, room_data)
    return {"status": "ok", "room": updated_room.__dict__}


@get_session
def delete_room(room_uid: UUID, request: Request, db_session):
    user = request.state.user  # Получаем данные пользователя из middleware

    room = Room.get_room_by_uid(db_session, room_uid)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.owner_uid != UUID(user["uid"]):
        raise HTTPException(status_code=403, detail="You are not the owner of this room")

    Room.delete_room(db_session, room_uid)
    return {"status": "ok", "message": "Room deleted successfully"}