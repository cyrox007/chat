# PostgreSQL pool observability v1

Checkpoint `0.6.30-alpha.1` adds a privacy-safe runtime view of the SQLAlchemy connection pool used by PubChat backend workers.

## Scope

Each Uvicorn/application process owns its own SQLAlchemy pool. Therefore:

- `GET /admin/operations/postgres-pool` reports **only the process that handled that request**;
- the response declares `scope=current_process` and `aggregation.cross_process=false`;
- one healthy response must not be interpreted as cluster-wide PostgreSQL capacity;
- cross-worker aggregation belongs to the later telemetry/exporter layer.

A standalone CLI is intentionally not provided: a new CLI process would create its own pool and would not observe the live web-worker pools.

## Capacity settings

```dotenv
DB_POOL_SIZE=20
DB_POOL_MAX_OVERFLOW=10
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_ALERT_UTILIZATION_PERCENT=85
DB_POOL_MIN_HEADROOM_CONNECTIONS=3
```

`DB_POOL_SIZE + DB_POOL_MAX_OVERFLOW` is the maximum connection capacity **per application process**. With multiple backend workers, production capacity planning must multiply this limit by the number of worker processes and leave room for migrations, maintenance jobs and other PostgreSQL clients.

The alert thresholds are observational only. They do not resize the pool, terminate requests or shed traffic.

## Admin endpoint

```text
GET /admin/operations/postgres-pool
```

The endpoint uses the existing admin operations permission boundary and returns aggregate counters only:

- configured pool and overflow capacity;
- checked-out and checked-in connections;
- current overflow;
- remaining headroom;
- utilization percentage;
- near-capacity health.

It does not expose the database URL, credentials, SQL text, SQL parameters, Account IDs or connection identities.

## Operational interpretation

A near-capacity result means the worker that served the request has crossed either the utilization threshold or the configured minimum headroom. Investigate sustained pressure together with PostgreSQL server connection counts, request latency/error rate and worker count.

Do not use a single sampled response as an SLO or as proof that every worker is healthy. A later observability checkpoint must aggregate per-worker/process telemetry and PostgreSQL server-side capacity before beta.

## CI contract

Contract tests pin the privacy boundary, healthy/near-capacity semantics and explicit per-process scope. The normal backend CI also imports the configured engine with bounded pool settings.

This checkpoint intentionally does not introduce a synthetic SQL microbenchmark: a runner-local microbenchmark would not represent production query mix, database size, network latency or lock contention.
