import logging
from logging.handlers import RotatingFileHandler

# Создаем логгер
def setup_logger(name, log_file='app.log', level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Хендлер для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Хендлер для записи в файл (опционально)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger