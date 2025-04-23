from .manager import ConnectionManager

# Глобальные экземпляры менеджеров подключений
private_manager = ConnectionManager()  # Для приватных сообщений
room_manager = ConnectionManager()    # Для комнатных чатов

__all__ = ['ConnectionManager', 'private_manager', 'room_manager']