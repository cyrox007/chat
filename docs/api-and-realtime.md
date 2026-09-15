# HTTP API и Realtime PubChat

## Общие правила

Backend — FastAPI. В development OpenAPI доступен по `/docs`, машинная схема — по `/openapi.json`.

Служебные endpoints:

```text
GET /health
GET /service/version
```

Новые домены используют versioned prefixes. Legacy routes остаются compatibility layer и не должны становиться основой нового клиента.

## Authentication

Короткоживущий bearer access token используется для HTTP requests и в browser SPA хранится только в памяти. Долговременная refresh session — HttpOnly cookie. Cookie-based state-changing flows защищены CSRF.

- `401` — authentication/session problem; клиент может попробовать refresh.
- `403` — authorization decision; его нельзя превращать в бесконечный refresh/reconnect.

## Основные API domains

### `/identity/v2`

Account/Persona/session/privacy: registration, login, refresh/logout, current identity, Persona/privacy update и privacy-aware profile projection.

### `/spaces/v1`

Living Spaces: discovery/create/update, membership, members/requests, invitations, rules/events/history и scoped management.

### `/social/v1`

People discovery, follow/unfollow, friend requests/friendship и Account-level block.

### `/moderation/v1`

Reports, manager queues, moderation actions, appeals и appeal review. Private metadata проверяется только после scoped authorization.

### `/appearance/v1`

Persona/Space cosmetic projections. Appearance наследует privacy/visibility основной сущности.

### `/activities/v1`

Activities, RSVP и Conversation Rounds. Участие требует active Space membership; creator/scoped manager управляет activity/round.

### `/achievements/v1`

Read-only earned achievements. Клиентского grant endpoint нет.

### `/activity-occurrences/v1` — In development

Concrete bounded occurrences recurring Activity.

```text
GET  /activity-occurrences/v1/activities/{activity_uid}
POST /activity-occurrences/v1/activities/{activity_uid}/sync
```

`GET` только читает уже materialized rows и не изменяет БД. `POST .../sync` — явная idempotent command для bounded materialization. Reminder reconciliation также использует тот же server-side materialization service.

### `/notifications/v1` — In development

Private Account-owned reminders/inbox.

Основные operations:

- explicit `POST /sync` reconciliation;
- unread count;
- notification list;
- mark one/read-all;
- batch reminder preferences for Space;
- set/delete Activity reminder.

Reminder preferences никогда не запрашиваются для чужого Account через API.

## Realtime v2

### Handshake без credentials в URL

1. SPA делает authenticated `POST /realtime/v2/tickets`.
2. Payload указывает target и при необходимости Space UID.
3. Backend возвращает короткоживущий one-time ticket + `websocket_path`.
4. SPA открывает WebSocket по чистому path.
5. Ticket отправляется первым frame.
6. Backend consume-ит ticket и подтверждает readiness.

Ticket scope/TTL и одноразовость проверяются server-side.

## Presence и multi-worker

Membership и presence — разные сущности. Membership durable в PostgreSQL; presence ephemeral в Redis.

WebSocket objects живут только внутри local worker. Redis pub/sub обеспечивает межworker delivery/control. Heartbeat продлевает connection и presence-index TTL. Listener восстанавливает subscription после transient Redis failure.

## Reconnect/resume

SPA использует состояния `connecting -> authenticating -> connected -> reconnecting/offline`. После reconnect восстанавливаются нужные subscriptions/context без full-page reload.

## Idempotency, rate limiting, backpressure

Message creation использует `frontId` как server-side idempotency key. Redis хранит ephemeral claims/rate limits. Local send имеет timeout, поэтому slow consumer не блокирует broadcast всего Space.

## Time contract

Новые API projections возвращают UTC timestamps с `Z`. Activity create/update требует datetime с explicit timezone offset, затем durable `starts_at` нормализуется в UTC.

**Текущее alpha-ограничение:** Activity пока не хранит отдельный IANA timezone name (`Europe/Berlin` и т.п.). Recurrence поэтому UTC-anchored. При переходе DST локальное wall-clock время recurring встречи может сдвинуться на час. Это зафиксированный pre-beta calendar-time hardening task; reminders `0.5.2` следуют текущему canonical UTC recurrence и не пытаются самостоятельно менять расписание.

## Ошибки

Новые endpoints используют HTTP status + структурированный `detail.error_type`.

- `404` — объект отсутствует либо намеренно скрыт privacy policy;
- `403` — действие запрещено;
- `409` — конфликт состояния/лимит;
- `422` — invalid DTO.

Privacy-sensitive API может намеренно отвечать `404`, чтобы не раскрывать факт существования ресурса.

## Правила нового API

1. Typed request DTO.
2. Никакого ORM `__dict__` как API.
3. Explicit public/private projection.
4. Authorization server-side.
5. Account-level block учитывается в social surfaces.
6. Pagination/batch вместо N+1.
7. GET не создаёт durable state.
8. Contract/regression coverage.
9. Credentials не попадают в URL.
10. Contract пригоден для SPA и будущих native clients.
