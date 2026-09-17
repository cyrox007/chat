from .manager import ConnectionManager

# Глобальные экземпляры менеджеров подключений
private_manager = ConnectionManager()  # Для приватных сообщений
room_manager = ConnectionManager()    # Для комнатных чатов

# Account-level suspension must disconnect sockets across every Uvicorn worker.
# Install after the manager instances exist to avoid circular imports.
from .account_control import install_account_control  # noqa: E402

install_account_control(private_manager, room_manager)

__all__ = ['ConnectionManager', 'private_manager', 'room_manager']
