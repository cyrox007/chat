# HTTP API и Realtime PubChat

## Общие правила

Backend — FastAPI. В development OpenAPI доступен по `/docs`, а машинная схема — по стандартному `/openapi.json`.

Версия приложения:

```text
GET /service/version
```

Health-check:

```text
GET /health
```

Новые продуктовые домены используют versioned prefixes. Legacy routes пока существуют как compatibility layer и не должны становиться основой нового клиента.

## Authentication model

### Access token

Короткоживущий bearer access token используется для authenticated HTTP requests. В browser SPA он хранится только в памяти процесса страницы.

### Refresh session

Долговременная сессия использует HttpOnly cookie. При reload SPA выполняет refresh flow и получает новый access token.

### CSRF

Cookie-based state-changing flows используют CSRF protection. SPA умеет получить CSRF cookie и повторить запрос при ожидаемом CSRF failure.

### 401 и 403

- `401` — session/authentication problem; клиент может попытаться refresh.
- `403` — authorization decision; клиент не должен автоматически считать его expired session.

## Основные API domains

### `/identity/v2`

Account/Persona/session/privacy.

Типовые операции:

- registration/login;
- refresh/logout;
- current identity;
- Persona update;
- privacy update;
- privacy-aware profile projection.

Подробности: [`identity-v2.md`](identity-v2.md).

### `/spaces/v1`

Living Spaces:

- discovery;
- create/read/update;
- membership/join/request;
- members/pending requests;
- invitations;
- rules/events/history;
- scoped management.

Space visibility и membership checks должны применяться backend к любому новому endpoint, который раскрывает Space data.

### `/social/v1`

Account-level social graph:

- discovery;
- follow/unfollow;
- friend request/accept/reject/remove;
- block/unblock.

### `/moderation/v1`

Transparent moderation:

- reports;
- manager queues;
- moderation actions;
- appeals;
- appeal review.

Private report metadata нельзя раскрывать до scoped authorization.

### `/appearance/v1`

Persona/Space cosmetic projections. Public appearance наследует privacy/visibility основной сущности.

### `/activities/v1`

Activities, RSVP и Conversation Rounds.

Activities требуют active Space membership для участия. Creator или scoped manager управляет activity/round.

### `/achievements/v1`

Read-only achievement API. Клиентского write/grant endpoint нет.

### `/activity-occurrences/v1` — In development

Concrete bounded occurrences для recurring Activities.

### `/notifications/v1` — In development

Private Account-owned reminder preferences и in-app inbox.

Основные operations development slice:

- list reminder preferences for Space;
- set/delete reminder preference;
- explicit sync/reconciliation;
- unread count;
- notification list;
- mark one/read-all.

GET endpoints не должны иметь side effects; materialization/reconciliation вызывается отдельным command request.

## Realtime v2

### Почему нет JWT в URL

Credentials в WebSocket URL могут попадать в access logs, proxy logs и monitoring. PubChat использует ticket handshake.

### Handshake

1. SPA выполняет authenticated HTTP request:

```text
POST /realtime/v2/tickets
```

2. В payload указывается target (`room`/messenger target) и при необходимости Space UID.
3. Backend возвращает короткоживущий one-time ticket и `websocket_path`.
4. SPA открывает WebSocket по чистому path без credential.
5. Ticket отправляется первым frame.
6. Backend consume-ит ticket и отвечает readiness event.

Ticket имеет TTL и scope и не предназначен для повторного использования.

## Realtime channels

### Space

Canonical route v2 не содержит bearer/token в path. После authorization backend дополнительно проверяет canonical active membership/restriction.

### Messenger

Отдельный realtime target для direct conversations. Privacy policy и block проверяются server-side.

## Presence

Presence distributed через Redis. Heartbeat обновляет connection state и TTL indexes. Presence не равна membership:

- membership — durable право/участие;
- presence — текущий online/realtime state.

UI обязан различать эти сущности.

## Pub/Sub и multi-worker

Локальный worker хранит только реальные WebSocket objects своих клиентов. Межworker events доставляются Redis pub/sub.

Control events, включая disconnect/restriction, также распространяются между workers.

Listener восстанавливает subscription после transient Redis failure.

## Reconnect/resume

SPA использует state machine:

```text
connecting -> authenticating -> connected
                     |             |
                     v             v
                reconnecting <- offline
```

После reconnect клиент восстанавливает контекст, subscriptions и небольшое окно данных вместо полной перезагрузки SPA.

## Idempotency

Message create использует client `frontId` как idempotency key. Защита существует server-side до durable write, поэтому reconnect/retry не должен создавать duplicate messages.

## Rate limiting и backpressure

Realtime message rate limiting хранится в distributed ephemeral layer. Local socket send имеет timeout: один slow consumer не должен блокировать broadcast всему Space.

## Time contract

Новые API projections должны возвращать UTC timestamps с явным `Z`.

Принимаемые datetime для Activity creation/update требуют explicit timezone. Backend нормализует durable value в UTC.

Legacy timestamps могут существовать в старых contracts; SPA compatibility normalization не должна становиться моделью для новых API.

## Ошибки

Новые endpoints стремятся возвращать структурированный `detail.error_type`. Клиент должен ориентироваться прежде всего на HTTP status + stable error type, а не на русскоязычный текст сообщения.

Типовые категории:

- `404` — ресурс недоступен или скрыт privacy policy;
- `403` — authenticated, но действие запрещено;
- `409` — конфликт состояния;
- `422` — invalid DTO/input.

Privacy-sensitive resources часто намеренно возвращают `404`, чтобы не раскрывать факт существования скрытого объекта.

## Правила добавления API

Новый endpoint должен:

1. Использовать typed Pydantic DTO.
2. Не сериализовать ORM через `__dict__`.
3. Иметь explicit public/private projection.
4. Проверять Account/Space authorization server-side.
5. Учитывать Account-level block там, где появляются люди/контент людей.
6. Использовать pagination/batch вместо N+1.
7. Не создавать state через GET.
8. Иметь contract/regression coverage.
9. Не передавать credentials в URL.
10. Быть пригодным для SPA и будущих native clients.
