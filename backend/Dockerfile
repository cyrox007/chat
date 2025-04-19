# Базовый образ
FROM python:3.13.3-alpine

# Установка системных зависимостей
RUN apk add --no-cache gcc musl-dev postgresql-dev

# Копирование requirements.txt и установка зависимостей
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip check

# Копирование исходного кода
COPY . .

# Команда запуска
CMD alembic upgrade head && python3 run_server.py