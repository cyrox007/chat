# PubChat Stage 6.2 — Multi-process WebSocket / Rolling Restart

Released checkpoint: `0.6.4-alpha.1`.

## Цель

Доказать, что Realtime v2 работает не только между несколькими `RealtimeService` objects в одном Python process, но и через реальные OS process boundaries с Uvicorn/FastAPI workers, общим Redis transport и настоящими WebSocket connections.

## CI rehearsal

GitHub Actions запускает dedicated integration test `tests.test_realtime_multiprocess_integration` после PostgreSQL migration checks, Redis distributed smoke и Redis restart/recovery drill.

Rehearsal выполняет следующий сценарий:

1. Запускается отдельный `RealtimeService` в test process при `DEBUG=False`.
2. Поднимаются два независимых Uvicorn/FastAPI process на разных TCP ports.
3. Все три process используют один Redis 7.2 и одну PostgreSQL integration DB.
4. Test process выдаёт one-time messenger tickets.
5. Каждый ticket consume-ится внутри другого Uvicorn process через `/ws/v2/messenger` и первый WebSocket auth frame.
6. Оба worker регистрируют distributed presence в Redis.
7. Test process публикует Redis realtime event для Account A и Account B; event доставляется worker process, владеющему соответствующим process-local WebSocket object.
8. Worker A останавливается как rolling-restart node, при этом Worker B продолжает обслуживать realtime event.
9. На том же port запускается replacement Worker A.
10. Клиент получает новый one-time ticket, повторно подключается и снова получает realtime event.

## Что доказано

- WebSocket objects остаются строго process-local;
- ticket storage/consume работает между реальными процессами через Redis;
- presence является distributed state и виден за пределами worker process;
- Redis pub/sub является authoritative fan-out между process boundaries;
- остановка одного worker не блокирует realtime traffic другого worker;
- после replacement process клиент может безопасно reconnect-иться с новым one-time ticket;
- rolling restart не требует переноса reusable credentials в WebSocket URL;
- существующие migration/recovery/frontend gates продолжают проходить в одном CI pipeline.

## Что checkpoint не утверждает

Этот baseline не закрывает все production realtime risks.

Остаются отдельно:

- slow-client/backpressure под burst/load;
- mass reconnect latency/capacity;
- Redis Sentinel/Cluster/managed failover topology;
- load distribution через внешний reverse proxy/load balancer;
- structured socket/Redis metrics и alerting.

## Почему ticket выдаётся test process

Цель checkpoint — проверить process boundary realtime transport, а не повторно тестировать HTTP login/session stack. One-time ticket создаётся production `RealtimeService` через общий Redis, а consume происходит production WebSocket auth path внутри Uvicorn process. HTTP ticket endpoint уже покрывается contract/security слоями Realtime v2.

## Инварианты

- production realtime не использует process-local fallback;
- reusable credential не появляется в WebSocket URL;
- новый connection после restart использует новый one-time ticket;
- один worker не владеет distributed presence целиком;
- Redis остаётся ephemeral transport/state layer, PostgreSQL — durable source of truth;
- restart одного worker не должен требовать restart остальных workers.