class UserValidationError(Exception):
    """Исключение для ошибок валидации пользователя"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)