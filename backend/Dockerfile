# Многоэтапная сборка для уменьшения размера финального образа
FROM python:3.13.3-alpine as builder

# Установка только необходимых build-зависимостей
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    postgresql-dev

# Создание и активация виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip check

# Финальный образ
FROM python:3.13.3-alpine

# Копируем только необходимое из builder-этапа
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка runtime зависимостей
RUN apk add --no-cache libpq

# Создание рабочей директории
WORKDIR /app
COPY . .

# Оптимизация для production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UVICORN_WORKERS=2 \
    UVICORN_TIMEOUT_KEEP_ALIVE=30

# Улучшенная команда запуска с uvloop и httptools
CMD ["sh", "-c", "alembic upgrade head && \
     uvicorn app:app \
     --host 0.0.0.0 \
     --port 9000 \
     --workers 2 \
     --loop uvloop \
     --http httptools \
     --timeout-keep-alive $UVICORN_TIMEOUT_KEEP_ALIVE"]