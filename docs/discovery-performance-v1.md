# Discovery performance v1

Checkpoint: `0.6.25-alpha.1`.

## Цель

После перехода organic discovery на multi-source candidate generation важно фиксировать не только корректность ranking, но и стоимость запроса к PostgreSQL.

Performance contract намеренно делится на две части:

- **query budget** — основной детерминированный CI guard против N+1 и роста количества DB round-trips;
- **broad wall-time ceiling** — грубый safety-net против катастрофической деградации, но не microbenchmark и не публичный SLA.

## Что измеряет profiler

`components.discovery.profiling.profile_discovery()` считает для одного discovery call:

- `result_count`;
- `statement_count`;
- `select_count`;
- суммарное cursor DB time;
- wall-clock time.

Profiler не сохраняет и не выводит:

- SQL parameters;
- Account/Persona/Space identifiers;
- search text;
- result payload;
- message/content fields.

## CI performance rehearsal

PostgreSQL integration fixture создаёт 260 Spaces и добавляет разные виды candidate context:

- active memberships;
- shared tags/purposes;
- recent messages;
- upcoming Events.

Это больше общего `DISCOVERY_POOL_LIMIT=200`, поэтому тест проверяет bounded поведение уже после насыщения candidate pool.

Текущие regression budgets:

- default `organic-v2`: не более **30 SQL statements**;
- explicit purpose-filter mode: не более **20 SQL statements**;
- wall-time ceiling каждого path: **5000 ms**.

Wall threshold специально широкий: shared GitHub runner не должен флапать из-за микросекундных различий. Если нужно оптимизировать p50/p95/p99, это отдельный production-like load task с репрезентативными данными и окружением.

## Operational CLI

Из backend directory:

```bash
python -m workers.discovery_profile \
  --viewer-uid <ACCOUNT_UUID>
```

Machine gate:

```bash
python -m workers.discovery_profile \
  --viewer-uid <ACCOUNT_UUID> \
  --max-statements 30 \
  --max-wall-ms 5000
```

Можно передать `--query`, `--purpose`, `--tag`, `--limit` и `--offset`.

CLI печатает только aggregate JSON profile. Viewer UUID используется как вход для выполнения policy/ranking и намеренно не попадает в output.

## Интерпретация

Рост wall-time при неизменном query count обычно означает:

- более дорогой plan;
- больше строк, обработанных внутри bounded queries;
- pool/IO pressure;
- lock contention.

Рост `statement_count` — более сильный regression signal и обычно означает добавление дополнительных round-trips или N+1.

Перед изменением query budget нужно сначала объяснить, почему новый round-trip действительно необходим; просто поднять threshold без анализа нельзя.

## Что остаётся

Этот checkpoint не закрывает весь performance workstream. До beta отдельно нужны:

- privacy/block regression на большом candidate set;
- production-like ranking p50/p95/p99;
- PostgreSQL pool saturation;
- Redis/realtime pool saturation;
- provider/host resource telemetry.
