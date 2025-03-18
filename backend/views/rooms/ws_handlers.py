from fastapi import WebSocketDisconnect
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from components.room.model import Room
from components.message.model import Message
from database import get_db_session

# Менеджер для хранения активных соединений
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket, room_uid: UUID, user_uid: UUID):
        if room_uid not in self.active_connections:
            self.active_connections[room_uid] = []
        self.active_connections[room_uid].append((websocket, user_uid))
        await websocket.accept()

    def disconnect(self, websocket, room_uid: UUID):
        if room_uid in self.active_connections:
            self.active_connections[room_uid] = [
                conn for conn in self.active_connections[room_uid] if conn[0] != websocket
            ]
            if not self.active_connections[room_uid]:
                del self.active_connections[room_uid]

    async def broadcast(self, room_uid: UUID, message: dict):
        if room_uid in self.active_connections:
            for connection, _ in self.active_connections[room_uid]:
                await connection.send_json(message)

manager = ConnectionManager()

async def handle_websocket_connection(websocket, room_uid: str, user):
    # Преобразуем room_uid в UUID
    try:
        room_uid = UUID(room_uid)
        user_uid = UUID(user["uid"])
    except ValueError:
        await websocket.close(code=1008, reason="Invalid room UID")
        return

    # Получаем сессию базы данных
    db_session = get_db_session()

    # Проверяем, существует ли комната
    room = Room.get_room_by_uid(db_session, room_uid)
    if not room:
        await websocket.close(code=1008, reason="Room not found")
        return

    # Подключаем пользователя к комнате
    await manager.connect(websocket, room_uid, user_uid)

    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            message_data = {
                "content": data,
                "sender_uid": str(user_uid),
                "room_uid": str(room_uid),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Сохраняем сообщение в базу данных
            new_message = Message.create_message(db_session, message_data)

            # Рассылаем сообщение всем участникам комнаты
            await manager.broadcast(room_uid, new_message.__dict__)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_uid)