# Realtime Redis pool profile v1

Checkpoint `0.6.27-alpha.1` добавляет bounded capacity/observability baseline для Redis connection pool, который обслуживает realtime v2.

## Зачем

До этого CI доказывал correctness Redis primitives, restart recovery, Sentinel promotion и multi-process WebSocket, но не измерял, насколько близко concurrent realtime workload подходит к лимиту connection pool.

Этот checkpoint не объявляет GitHub runner production benchmark. Его задача:

- видеть текущие `in-use / available / created / headroom` значения pool;
- обнаруживать приближение к configured capacity;
- прогонять реальные realtime primitives при bounded concurrency возле небольшого pool limit;
- падать по error/saturation gate, а не по нестабильному «должно быть быстрее N миллисекунд» микробенчмарку;
- не раскрывать Redis URL, credentials, ticket values или Account identifiers.

## Runtime metrics

Admin-only endpoint:

```
GET /admin/operations/realtime-redis
```

Возвращает aggregate pool state:

- topology mode: direct / sentinel;
- configured max connections;
- current in-use connections;
- currently available pooled connections;
- created pooled connections;
- remaining headroom;
- utilization percent;
- near-capacity state.

Thresholds:

```dotenv
REDIS_POOL_ALERT_UTILIZATION_PERCENT=85
REDIS_POOL_MIN_HEADROOM_CONNECTIONS=5
```

Это observability thresholds. Они не меняют размер pool, retry policy и не выполняют traffic shedding.

## Bounded profile CLI

Для staging/controlled rehearsal:

```bash
cd backend
python -m workers.realtime_pool_profile \
  --operations 120 \
  --concurrency 10 \
  --max-error-rate-percent 0 \
  --max-p95-ms 2000 \
  --max-saturation-samples 0 \
  --require-healthy
```

Каждая profile operation использует production `RealtimeService` primitives:

1. one-time ticket issue + consume;
2. presence register + heartbeat/touch + unregister;
3. idempotency claim + release.

Generated Account/event/connection identifiers остаются внутри profile process и не включаются в report.

## CI rehearsal

CI специально уменьшает pool до 12 connections и запускает concurrency 10, оставляя место для долгоживущей PubSub connection и небольшого command headroom.

Functional run #748 на GitHub-hosted runner показал:

- 120 / 120 operations completed;
- 0 errors;
- peak 11 in-use из 12 configured connections;
- peak utilization 91.67%;
- 0 saturation samples;
- p95 около 19 ms в этом конкретном CI run.

Последняя цифра не является production SLO или capacity promise. Hardware, network topology, Redis provider, TLS, Sentinel/managed proxy и реальный command mix изменят latency/throughput.

## Privacy boundary

Report/endpoint не включают:

- `REDIS_URL`, hostnames или credentials;
- one-time ticket values;
- Account/Persona identifiers;
- presence connection IDs;
- event IDs;
- Redis keys или command payloads.

Error report хранит только Python exception class counters, без exception text.

## Что ещё не закрыто

Этот baseline не заменяет:

- production-like sustained soak test;
- reverse-proxy/WebSocket mass reconnect profile;
- managed/Sentinel topology metrics: current master, promotion duration, replication lag;
- command timeout/error-rate metrics over time;
- alert backend/dashboard/on-call delivery;
- capacity planning на реальном deployment hardware.

Следующий operations slice должен строиться на этих metrics и реальных production-like measurements, а не увеличивать `REDIS_MAX_CONNECTIONS` вслепую.
