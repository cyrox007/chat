# PubChat Stage 6.2 — Redis Restart Recovery

Released checkpoint: `0.6.3-alpha.1`.

## Цель

Доказать, что production realtime не только работает на живом Redis, но и восстанавливается после реального restart Redis без перезапуска Python/FastAPI process.

## CI drill

GitHub Actions использует реальный service container Redis 7.2. Dedicated integration test получает container id и выполняет полный outage/recovery cycle.

1. Два `RealtimeService` instance стартуют при `DEBUG=False`.
2. Baseline ticket создаётся одним instance и consume-ится другим.
3. Redis container останавливается через Docker.
4. Production publish во время outage обязан завершиться `RealtimeUnavailable`; process-local fallback запрещён.
5. Тот же Redis container запускается снова.
6. Test ждёт успешный `PING`.
7. Те же, уже созданные `RealtimeService` objects снова выполняют ticket issue/consume.
8. Pub/Sub listener автоматически восстанавливает subscription; event от одного instance снова приходит callback второго.
9. Cleanup гарантированно запускает Redis, даже если assertion упал во время outage.

## Что доказано

- Redis outage видим приложению и не маскируется local fallback;
- redis-py connection pool восстанавливает normal command path после restart;
- `RealtimeService` не требуется пересоздавать;
- one-time ticket path восстанавливается на тех же service objects;
- pub/sub listener автоматически пересоздаёт subscription после разрыва;
- durable PostgreSQL state не участвует в Redis recovery и не теряется.

## Что ещё не доказано

- реальный multi-process Uvicorn/WebSocket traffic;
- browser reconnect через rolling restart backend workers;
- slow-consumer/backpressure под нагрузкой;
- Redis Sentinel/Cluster/managed failover;
- latency/capacity при массовом reconnect;
- гарантии сохранения ephemeral presence/ticket state через Redis restart — такие данные по определению могут исчезнуть и должны восстанавливаться протоколом клиента.

## Эксплуатационный смысл

Redis является ephemeral layer. После полного restart допустима потеря presence, unconsumed tickets, rate-limit/idempotency TTL keys и transient pub/sub messages. Система должна не сохранять эти ключи любой ценой, а корректно восстановить transport и заставить клиент получить новый ticket/reconnect там, где это необходимо.

## Инварианты

- production outage не превращается в process-local mode;
- recovery не требует process restart;
- credential никогда не переносится в WebSocket URL;
- durable membership/messages/moderation/history остаются PostgreSQL state;
- reconnect/reissue безопаснее попытки сделать ephemeral Redis state durable.
