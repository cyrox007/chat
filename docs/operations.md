# Эксплуатация PubChat

## Статус

Проект находится в alpha. Документ описывает текущую production-oriented конфигурацию, но не означает, что production launch gate уже пройден.

## Обязательные сервисы

- FastAPI backend.
- PostgreSQL как durable source of truth.
- Redis для production realtime/distributed state.
- Собранный Vue SPA.
- Reverse proxy с HTTPS и WebSocket support.

## Environment

Backend использует `backend/.env.example` как перечень основных параметров.

Критически важны:

- `FRONTEND_URL` — allowlist origins CORS;
- `DB_*` — PostgreSQL;
- `REDIS_URL` — Redis;
- `JWT_ACCESS_SECRET_KEY`;
- `JWT_REFRESH_SECRET_KEY`;
- `CSRF_SECRET_KEY`.

Три security secret должны быть разными и длиной не менее 32 символов. Production не должен использовать значения из `.env.example`.

Frontend:

- `VITE_API_BASE_URL` — HTTP API origin;
- `VITE_API_WS_SERVER_URL` — необязательный WebSocket origin. Если не задан, SPA преобразует API `http/https` в `ws/wss`.

## HTTPS и cookies

Production должен работать через HTTPS. Refresh session использует HttpOnly cookie, а realtime — `wss://` за TLS termination/reverse proxy.

Proxy должен корректно передавать WebSocket Upgrade/Connection headers и не логировать секретные credentials. Realtime v2 специально не помещает credential в WebSocket URL.

## Redis

В production Redis обязателен. Он обслуживает одноразовые socket tickets, pub/sub, distributed presence, heartbeat state, rate limiting и idempotency.

Если Redis недоступен, production realtime не должен молча переходить в process-local режим и создавать ложное ощущение multi-worker correctness.

## PostgreSQL и migrations

Перед deployment:

1. Создать backup.
2. Проверить одну migration head командой `alembic heads`.
3. Выполнить rehearsal на копии production/legacy schema для значимого обновления.
4. Запустить `alembic upgrade head`.
5. Только затем поднимать application workers новой версии.

На alpha-стадии destructive migrations без backup/rehearsal недопустимы.

## Workers и realtime

ConnectionManager хранит реальные WebSocket objects только локально процессу. Distributed events/presence идут через Redis, поэтому разрешён multi-worker deployment при исправно работающем Redis.

Проверяйте:

- pub/sub reconnect;
- heartbeat/presence TTL;
- cross-worker delivery;
- cross-worker restriction/disconnect;
- reconnect клиента после rolling restart.

## Uploads

Текущая реализация использует локальный `backend/uploads` и отдаёт `/uploads` через FastAPI.

Это ограничение для горизонтального deployment: локальные файлы одного instance не существуют на другом. До production scaling требуется shared volume или object storage/CDN adapter.

## Health и version

- `GET /health` — базовый health endpoint.
- `GET /service/version` — версия backend.
- FastAPI metadata также использует канонический `VERSION`.

После deployment сверяйте backend version с ожидаемым release и frontend build version.

## Observability

Полный observability stack пока не завершён. До beta необходимы:

- structured application logs;
- metrics для HTTP/realtime/Redis/PostgreSQL;
- error tracking;
- latency/error-rate dashboards;
- alerting;
- incident/status procedures.

Нельзя логировать access/refresh token material или WebSocket tickets.

## Backup

Минимальная стратегия перед production launch должна включать:

- регулярный PostgreSQL backup;
- проверку restore procedure;
- backup/migration strategy для uploads/object storage;
- секреты отдельно от repository backup.

## Release deployment checklist

1. Все CI jobs зелёные на exact versioned head.
2. `VERSION` и `CHANGELOG.md` совпадают.
3. Database backup выполнен.
4. Migration rehearsal пройден для рискованной схемы.
5. `alembic heads` показывает одну head.
6. Secrets и CORS origins проверены.
7. Redis/PostgreSQL доступны.
8. Frontend production build выполнен.
9. `/health` и `/service/version` проверены.
10. Login/refresh, Space realtime и DM smoke test пройдены.

## Пока не заявлено как готовое

- Docker Compose/Kubernetes manifests;
- shared object storage;
- background notification worker/native push;
- production-like load test results;
- формальная PostgreSQL/Redis compatibility matrix;
- fully automated rollback.
