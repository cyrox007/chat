# PubChat Stage 6.2 — Redis Realtime Integration

Released checkpoint: `0.6.2-alpha.1`.

## Цель

Закрепить production-семантику realtime v2 на настоящем Redis, а не только unit/fallback тестами.

CI поднимает Redis `7.2` рядом с PostgreSQL. Dedicated integration test принудительно использует `DEBUG=False`, поэтому process-local fallback не участвует в проверке.

## Что проверяется

Два независимых `RealtimeService` instance подключаются к одному Redis и доказывают общую distributed state.

### One-time tickets

- ticket создаётся одним instance;
- второй instance может его consume-ить;
- повторный consume возвращает отсутствие ticket;
- TTL хранится в Redis и истёкший ticket больше не принимается.

### Presence

- connection регистрируется одним instance;
- другой видит Account online и получает его в room presence;
- unregister через другой instance удаляет distributed presence.

### Rate limiting

Counter общий для service instances. Лимит нельзя обойти чередованием запросов между несколькими web workers.

### Idempotency

`SET NX` claim виден всем instance. Повторный event id отклоняется cross-worker; release после неуспешного persistence снова разрешает безопасный retry.

### Pub/Sub

Callback, зарегистрированный во втором service instance, получает event, опубликованный первым. Проверяется protocol v2 payload, поэтому test не удовлетворяется process-local dispatch.

## CI contract

Backend CI использует:

- PostgreSQL 16;
- Redis 7.2;
- `REDIS_URL=redis://127.0.0.1:6379/0`;
- `PUBCHAT_REDIS_INTEGRATION=1` только для dedicated integration smoke.

После test Redis DB очищается, listener tasks корректно останавливаются.

## Что checkpoint доказывает

- Redis 7.2 является фактически CI-проверенным baseline для текущего realtime implementation;
- ticket/presence/rate-limit/idempotency state действительно distributed;
- pub/sub проходит между независимыми `RealtimeService` objects;
- production Redis path работает при `DEBUG=False`;
- PostgreSQL/recovery gates продолжают проходить в том же CI pipeline.

## Что checkpoint ещё не доказывает

Следующие задачи Stage 6.2 остаются отдельными hardening slices:

- Redis restart и восстановление соединения без process restart;
- потеря/восстановление pub/sub subscription;
- реальные multi-process Uvicorn/WebSocket scenarios;
- reconnect клиента после rolling restart;
- slow-consumer/backpressure под нагрузкой;
- измеренная TTL/rate-limit точность под concurrency;
- Redis Sentinel/Cluster/managed-service topology;
- production capacity/latency sizing.

## Инварианты

- production realtime не должен молча переходить в process-local fallback;
- credential не передаётся в WebSocket URL;
- one-time ticket остаётся scoped и consume-once;
- rate limit/idempotency нельзя обойти сменой web worker;
- presence — ephemeral Redis state, membership — durable PostgreSQL state;
- Redis failure/recovery не должен менять durable social/domain data.
