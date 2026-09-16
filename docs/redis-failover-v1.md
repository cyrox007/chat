# Redis Sentinel failover v1

Этот документ описывает Stage 6.2 high-availability contract для realtime Redis. Он дополняет [`redis-realtime-integration-v1.md`](redis-realtime-integration-v1.md) и [`redis-recovery-v1.md`](redis-recovery-v1.md).

## Цель

PubChat должен уметь пережить потерю текущего Redis master без перехода в process-local fallback и без обязательного restart FastAPI/Uvicorn workers.

PostgreSQL остаётся durable source of truth. Redis по-прежнему хранит ephemeral realtime state: one-time tickets, presence/heartbeat, rate limits, idempotency windows и pub/sub transport.

## Поддерживаемые topology modes

### Direct

Backward-compatible режим:

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

Он подходит для development, single-node production rehearsal и существующих deployments, но сам по себе не даёт automatic master promotion.

### Sentinel

Sentinel mode включается только когда заданы оба параметра:

```env
REDIS_SENTINEL_NODES=10.0.0.11:26379,10.0.0.12:26379,10.0.0.13:26379
REDIS_SENTINEL_MASTER=pubchat-master
REDIS_SENTINEL_MIN_OTHER_SENTINELS=1
REDIS_DB=0
```

При наличии Sentinel configuration она имеет приоритет над `REDIS_URL`. Частично заданная Sentinel config считается ошибкой deployment configuration.

Authentication master и Sentinel nodes настраивается раздельно через `REDIS_USERNAME`/`REDIS_PASSWORD` и `REDIS_SENTINEL_USERNAME`/`REDIS_SENTINEL_PASSWORD`.

## Runtime contract

`RealtimeService` не хранит фиксированный master host. В Sentinel mode redis-py `SentinelConnectionPool` запрашивает актуальный master у Sentinel и закрывает cached connections к старому master после изменения адреса.

При failover:

1. commands против погибшего master могут временно завершаться ошибкой;
2. Sentinel достигает quorum и promotes replica;
3. новый command connection обнаруживает promoted master;
4. тот же `RealtimeService` object продолжает работать;
5. PubSub listener закрывает потерянную subscription и создаёт новую через тот же failover-aware pool;
6. клиенты WebSocket используют существующий reconnect/ticket protocol там, где transient outage оборвал transport.

Production не включает local fallback ни во время failover, ни при Sentinel outage.

## Ephemeral state и возможная потеря

Redis replication асинхронна. Поэтому при аварийном promotion последние ещё не реплицированные ephemeral keys/events могут быть потеряны.

Это допустимо только для данных, которые уже определены как ephemeral:

- неиспользованный one-time ticket можно запросить заново;
- presence восстанавливается heartbeat/reconnect;
- pub/sub не является durable queue;
- rate/idempotency windows могут кратковременно потерять часть transient state.

Message history, memberships, sanctions, delivery ledger и другие durable данные не должны переноситься в Redis ради failover.

## CI topology rehearsal

Integration harness поднимает на runner:

- Redis master `127.0.0.1:6380`;
- replica `127.0.0.1:6381`;
- три Sentinel process на `26379..26381` с quorum `2`;
- два независимых `RealtimeService` objects.

Проверяется:

- Sentinel topology client стартует без `REDIS_URL`;
- ticket issue/consume работает до failover;
- bounded concurrent ticket burst работает до failover;
- current master container реально останавливается;
- Sentinels promote replica на `6381`;
- те же Python service objects восстанавливают ticket issue/consume;
- bounded ticket burst проходит после promotion;
- PubSub listener пересоздаёт subscription и принимает event после promotion.

Тест не измеряет универсальный production throughput и не превращает CI runner в capacity benchmark. Его задача — доказать bounded concurrency и correctness через реальный topology change.

## Production topology guidance

Для production HA необходимы независимые failure domains. Три Sentinel process на одном VPS полезны для protocol rehearsal, но не защищают от потери самого VPS.

Минимальная production-like схема должна разводить Redis master/replica и Sentinel quorum по разным hosts/zones насколько позволяет инфраструктура. Quorum, replication lag, persistence и backup policy задаются вместе с RPO/RTO, а не выбираются только из CI значений.

## Observability

До beta нужны metrics/alerts минимум для:

- current master identity / topology changes;
- Sentinel master discovery failures;
- Redis command error rate/timeouts;
- promotion duration;
- replication link/lag;
- PubSub reconnect count/time;
- realtime ticket/presence errors во время failover;
- pool saturation.

Credentials и ticket values в logs/metrics запрещены.
