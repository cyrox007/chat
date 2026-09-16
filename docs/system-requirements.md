# Системные требования PubChat

## Поддерживаемый development baseline

Ниже указана конфигурация, которая фактически проверяется CI проекта и поэтому является основным ориентиром для разработки.

- Python `3.12`.
- Node.js `20`.
- npm с `package-lock.json` и установкой через `npm ci`.
- PostgreSQL `16` — текущий CI-проверенный persistent datastore baseline.
- Redis `7.2` — текущий CI-проверенный production-realtime baseline.
- Современный браузер с поддержкой ES modules, WebSocket, cookies, Service Worker, Web App Manifest и CSS `color-mix()`.

CI выполняется на Ubuntu Linux. Backend requirements включают `uvloop`, поэтому для Windows рекомендуется WSL2/Linux development environment. Нативный Windows не является текущим проверенным baseline.

## PostgreSQL

Проект использует SQLAlchemy 2, asyncpg и Alembic. PostgreSQL 16 теперь фактически проходит в CI:

- clean historical `alembic upgrade head`;
- `alembic check` zero-drift gate;
- async integration smoke;
- synthetic legacy-data rehearsal;
- custom-format backup/restore recovery drill.

Это делает PostgreSQL 16 проверенным baseline текущей alpha-линии. Другие поддерживаемые major-версии пока не заявляются как formal compatibility matrix.

Минимально необходимы:

- отдельная база данных;
- пользователь с правами на создание/изменение таблиц для выполнения Alembic migrations;
- UTF-8 database encoding;
- доступ backend и reminder worker к host/port базы.

## Redis

Redis server необходим в production. Redis 7.2 теперь является фактически CI-проверенным baseline для realtime v2.

Dedicated integration test работает при `DEBUG=False` и проверяет на реальном Redis:

- WebSocket one-time tickets и consume-once semantics;
- ticket TTL;
- pub/sub между независимыми realtime service instances;
- distributed presence;
- shared realtime rate limiting;
- shared idempotency claims/release.

В `DEBUG=True` realtime service всё ещё допускает локальные development fallback-механизмы, но они не заменяют distributed Redis operation и не используются в production-semantics integration test.

Использование Redis в PubChat:

- WebSocket one-time tickets;
- pub/sub между workers;
- distributed presence;
- heartbeat state;
- realtime message rate limiting;
- idempotency claims;
- cross-worker control events.

Redis restart/recovery, Sentinel/Cluster/managed topology и production capacity matrix ещё относятся к pre-beta hardening.

## CPU и память

Жёсткие минимальные аппаратные требования пока не измерены нагрузочными тестами. Для локальной разработки практический baseline:

- 2 CPU cores;
- 4 GB RAM минимум;
- 8 GB RAM предпочтительно при одновременном PostgreSQL + Redis + backend + Vite;
- несколько гигабайт свободного диска для зависимостей, БД и uploads.

Это не production sizing. До beta обязательны load tests и capacity planning, включая realtime Redis и reminder reconciliation worker.

## Сеть и порты по умолчанию

- Frontend Vite: `5173`.
- Backend FastAPI/Uvicorn: `9000`.
- PostgreSQL: `5432`.
- Redis: `6379`.

Порты PostgreSQL/Redis/backend настраиваются через environment variables. Frontend API endpoint задаётся `VITE_API_BASE_URL`.

## Требования браузера

Основной UX проектируется mobile-first, но SPA работает как обычное web application и installable PWA в поддерживающих браузерах.

Требуется:

- JavaScript включён;
- cookies разрешены для refresh/CSRF flow;
- WebSocket доступен через сеть/reverse proxy;
- Service Worker/Web App Manifest — для installability и offline shell;
- Local Storage используется только для несекретных UX-данных и cached shell state; access JWT туда не записывается.

Для production обязателен HTTPS: долговременная авторизация использует secure HttpOnly cookies, WebSocket должен работать через `wss://`, а service worker требует secure context. `localhost` допускается браузерами как development exception.

PWA installation зависит от поддержки конкретного браузера/OS. Если `beforeinstallprompt` недоступен, PubChat остаётся обычным SPA; core-функции не должны зависеть от installability.

## Reminder worker

Background reconciliation запускается отдельным CLI process:

```bash
cd backend
python -m workers.notification_reconciler
```

Для production-like фоновых reminders требуется внешний scheduler. FastAPI workers сами scheduler не запускают.

Worker использует ту же Python/PostgreSQL среду, что backend, и не требует отдельного runtime stack. Одновременные запускаемые экземпляры координируются PostgreSQL row-lock/cursor state.

## Файловое хранилище

Текущая реализация поддерживает локальный каталог `backend/uploads`. По умолчанию максимальный размер файла — 10 MiB, число файлов в одной операции ограничивается настройкой `MAX_FILES_LIMIT`.

Локальное хранение подходит для разработки. Перед горизонтальным production deployment нужен shared/object storage layer; иначе разные backend instances не будут видеть одинаковые локальные файлы.

## Что пока не считается гарантированно поддерживаемым

- native Windows backend без WSL2;
- PostgreSQL major кроме CI-validated 16;
- Redis major кроме CI-validated 7.2;
- Redis restart/failover/Cluster/Sentinel как уже доказанные сценарии;
- multi-region deployment;
- object storage/CDN как уже завершённая функция;
- browser/native push;
- offline messaging/private-data synchronization;
- Kubernetes/Docker Compose — готовых deployment manifests в репозитории сейчас нет;
- production sizing без нагрузочного теста.
