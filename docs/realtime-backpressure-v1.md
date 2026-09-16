# PubChat Stage 6.2 — Realtime Backpressure

Released checkpoint: `0.6.5-alpha.1`.

## Цель

Не допустить, чтобы один медленный или зависший WebSocket consumer задерживал Redis/pub-sub fan-out другим пользователям на том же Uvicorn worker.

## Модель

Каждый process-local WebSocket получает собственный `OutboundPump`:

- bounded `asyncio.Queue` хранит ожидающие outbound frames;
- один sender task последовательно отправляет frames и сохраняет порядок;
- Redis/pub-sub callback только кладёт payload в очередь и не ждёт network write;
- размер очереди ограничен `REALTIME_OUTBOUND_QUEUE_SIZE`;
- один socket write ограничен `REALTIME_SEND_TIMEOUT_SECONDS`.

По умолчанию:

- `REALTIME_OUTBOUND_QUEUE_SIZE=64`;
- `REALTIME_SEND_TIMEOUT_SECONDS=5`.

## Slow-consumer policy

Consumer считается непригодным для продолжения realtime-сессии, когда:

1. его outbound queue переполнена (`queue_full`); или
2. отправка одного frame превышает send timeout (`send_timeout`).

Такой WebSocket закрывается изолированно с code `1013` (`Try Again Later`) и reason `Realtime client too slow`.

Другие sockets того же Account, Space или worker продолжают работу.

Ошибка конкретного socket не должна превращаться в глобальный Redis/realtime outage.

## Ordering

В пределах одного WebSocket порядок frames сохраняется одним sender task.

Между разными sockets общей ordering guarantee нет и не требуется: каждый connection имеет собственную очередь и собственную скорость доставки.

Canonical message ordering по-прежнему определяется persisted payload (`uid`, timestamps, recent-window resume), а не скоростью конкретного network socket.

## Почему прежнего send timeout было недостаточно

До этого fan-out делал concurrent `send_json()` через `asyncio.gather()`. Быстрые sockets получали frame параллельно, но сам Redis callback ждал завершения всех send operations либо их timeout. Один stalled consumer мог удерживать обработку следующего Redis event до `REALTIME_SEND_TIMEOUT_SECONDS`.

Bounded outbound pumps разделяют ingress и network delivery: callback заканчивается после enqueue, а timeout конкретного consumer обрабатывается его sender task.

## Проверки

`tests/test_realtime_backpressure.py` детерминированно проверяет:

- сохранение порядка на fast consumer;
- queue overflow без ожидания send timeout;
- `queue_full` isolation для blocked consumer;
- `send_timeout` isolation для stalled send.

Полный CI дополнительно повторно проходит:

- PostgreSQL clean migration/schema drift;
- backend contract suite;
- PostgreSQL integration;
- Redis distributed realtime integration;
- Redis restart/recovery;
- real multi-process Uvicorn/WebSocket rolling restart;
- legacy migration rehearsal;
- PostgreSQL backup/restore;
- frontend security/PWA/lifecycle/build gates.

## Ограничения checkpoint

Этот checkpoint не является полной capacity-моделью production traffic.

Следующие отдельные задачи:

- Redis failover topology;
- Redis/pub-sub и reconnect capacity profiling;
- observability/metrics для queue depth, slow-consumer eviction и delivery latency;
- production-like load profile с реальными concurrency targets.

## Инварианты

- slow consumer не блокирует fan-out другим sockets;
- outbound memory на один socket ограничена;
- порядок frames внутри одного socket сохраняется;
- backpressure не превращается в purchasable priority или reputation mechanic;
- reconnect после `1013` использует обычный Realtime v2 flow с новым one-time ticket.