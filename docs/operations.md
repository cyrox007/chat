# Эксплуатация PubChat

## Статус

Проект находится в alpha. Документ описывает текущую production-oriented конфигурацию, но не означает, что production launch gate уже пройден.

## Обязательные сервисы

- FastAPI backend за systemd-owned persistent listener.
- PostgreSQL как durable source of truth.
- Redis для production realtime/distributed presence/context.
- Собранный Vue SPA/PWA shell.
- Reverse proxy с HTTPS и WebSocket support.
- Внешние scheduler units для background workers, если reminder/email функции включены.

## Environment

Backend использует `backend/.env.example` как перечень основных параметров.

Критически важны:

- `FRONTEND_URL` — allowlist origins CORS и canonical frontend destination;
- `DB_*` — PostgreSQL;
- direct `REDIS_URL` либо complete Redis Sentinel topology;
- `JWT_ACCESS_SECRET_KEY`;
- `JWT_REFRESH_SECRET_KEY`;
- `CSRF_SECRET_KEY`.

Три security secret должны быть разными и длиной не менее 32 символов. Production не должен использовать значения из `.env.example`.

Для unread-Messenger email worker дополнительно нужны `MESSAGE_EMAIL_SMTP_HOST` и `MESSAGE_EMAIL_FROM_EMAIL`; SMTP username/password задаются только парой. STARTTLS и implicit SSL взаимоисключающие. Сам внешний канал всё равно остаётся opt-in на уровне Account preference.

Frontend:

- `VITE_API_BASE_URL` — HTTP API origin;
- `VITE_API_WS_SERVER_URL` — необязательный WebSocket origin. Если не задан, SPA преобразует API `http/https` в `ws/wss`.

## HTTPS, cookies и PWA

Production должен работать через HTTPS. Refresh session использует HttpOnly cookie, realtime — `wss://`, а service worker/PWA installability требуют secure context. `localhost` остаётся standard browser exception для development.

Proxy должен корректно передавать WebSocket Upgrade/Connection headers и не логировать credentials. Realtime v2 не помещает credential в WebSocket URL.

Service worker обслуживает application shell/static assets и не должен кэшировать API/auth/realtime responses или credentials.

## Redis

В production Redis обязателен. Он обслуживает one-time socket tickets, pub/sub, distributed presence, active context, heartbeat state, rate limiting и idempotency.

Если Redis недоступен, production realtime/message external-delivery policy не должен молча переходить в process-local режим. Offline email worker fail-closed, потому что без distributed presence нельзя безопасно утверждать, что Account отсутствует.

## PostgreSQL и migrations

Перед deployment:

1. Создать backup.
2. Проверить одну migration head командой `alembic heads`.
3. Выполнить rehearsal на копии production/legacy schema для значимого обновления.
4. Запустить `alembic upgrade head`.
5. Только затем поднимать application workers новой версии.

На alpha-стадии destructive migrations без backup/rehearsal недопустимы.

## Web workers и realtime

ConnectionManager хранит реальные WebSocket objects только локально процессу. Distributed events/presence идут через Redis, поэтому разрешён multi-worker deployment при исправно работающем Redis.

Проверяйте pub/sub reconnect, heartbeat/presence TTL, cross-worker delivery/restriction и reconnect клиента после rolling restart.

Routine production deploy выполняется через `bash ops/deploy.sh`; legacy full-restart updater не должен использоваться после перехода на persistent socket deployment.

## Activity reminder reconciliation worker

Ручной запуск:

```bash
cd backend
python -m workers.notification_reconciler
```

В production этот command запускается внешним scheduler'ом. Worker намеренно не встроен в FastAPI lifecycle: иначе каждый Uvicorn worker мог бы выполнять собственный background sweep.

`NotificationWorkerState` хранит durable cursor, run bounded по batch/max-batches, а `FOR UPDATE SKIP LOCKED` предотвращает overlap одного cursor sweep. Crash может повторить window, но notification dedupe делает повтор безопасным.

## Unread Messenger email worker

Checkpoint `0.6.8-alpha.1` добавляет отдельный re-engagement worker только для Messenger. Offline Space chat не участвует в email delivery.

CLI:

```bash
cd backend
python -m workers.unread_dm_email_nudge --stage queue
python -m workers.unread_dm_email_nudge --stage deliver
python -m workers.unread_dm_email_nudge --stage all
```

Production units устанавливаются после заполнения SMTP settings:

```bash
cd /home/projects/pubchat
bash ops/install-message-email-worker.sh
```

Installer выполняет security/realtime/SMTP preflight, устанавливает `pubchat-message-email.service` + `.timer`, включает timer и сразу запускает один bounded cycle. По умолчанию timer проверяет работу примерно раз в 15 минут с randomized delay.

Delivery contract:

- candidate queue только для inactive Account с verified email, opt-in и unread DM;
- Account-level cooldown не обходится новым входящим сообщением;
- current Redis presence, preference, verified email, unread state и block/privacy повторно проверяются перед send;
- PostgreSQL ledger не хранит destination email и message body;
- network send защищён expiring claim lease; concurrency использует `FOR UPDATE SKIP LOCKED`;
- retryable SMTP failures получают bounded exponential backoff, terminal failures завершаются как `failed`;
- если пользователь снова online — delivery переносится без расходования retry budget;
- opt-out/read/block transition переводит stale delivery в `suppressed`.

SMTP не даёт абсолютный exactly-once на границе «relay принял письмо, process умер до DB commit». PubChat использует стабильный `Message-ID` для одного delivery UID, но не обещает downstream дедупликацию со стороны любого relay.

Подробности: [`message-email-delivery-v1.md`](message-email-delivery-v1.md).

## PWA/offline contract

Offline mode пока означает application shell, а не offline private messaging. Не кэшируются messages, API projections, notification inbox, auth/session responses и другие приватные fetch/XHR данные.

Web Push является следующим отдельным delivery adapter и не должен менять этот cache contract.

## Uploads

Текущая реализация использует локальный `backend/uploads` и отдаёт `/uploads` через FastAPI. Для горизонтального deployment нужен shared volume или object storage/CDN adapter.

## Health и version

- `GET /health/live` — process liveness;
- `GET /health/ready` — dependency-aware PostgreSQL + Redis readiness;
- `GET /service/version` — версия backend;
- FastAPI metadata использует канонический `VERSION`.

После deployment сверяйте backend version с ожидаемым release и frontend build version.

## Observability

Полный observability stack пока не завершён. До beta необходимы structured logs, HTTP/realtime/Redis/PostgreSQL metrics, email/Web Push worker/provider metrics, error tracking, dashboards/alerting и incident/status procedures.

Нельзя логировать access/refresh tokens, WebSocket tickets, SMTP credentials, destination email из delivery attempts или private message body.

## Backup

Минимальная стратегия перед production launch должна включать регулярный PostgreSQL backup, проверенный restore, storage backup policy и хранение secrets отдельно от repository backup.

## Release deployment checklist

1. Все CI jobs зелёные на exact versioned head.
2. `VERSION` и `CHANGELOG.md` совпадают.
3. Database backup выполнен.
4. Migration rehearsal пройден для рискованной схемы; `alembic heads` показывает одну head.
5. Secrets/CORS/Redis/PostgreSQL проверены.
6. Frontend production build выполнен staged publish path.
7. `/health/live`, `/health/ready`, `/service/version` проверены.
8. Login/refresh, Space realtime, DM и notification smoke tests пройдены.
9. Если email nudge включается — SMTP preflight + `ops/install-message-email-worker.sh` + timer status проверены отдельно.

## Пока не заявлено как готовое

- Docker Compose/Kubernetes production manifests;
- shared object storage;
- Web Push/native push;
- offline messaging/private data cache;
- production-like load test results;
- формальная PostgreSQL/Redis compatibility matrix;
- fully automated rollback.
