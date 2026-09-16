# PubChat version quick reference

- Current release: **0.6.5-alpha.1**.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics and restart recovery; real multi-process Uvicorn/WebSocket delivery; rolling-restart reconnect with fresh one-time tickets; bounded per-socket outbound queues with slow-consumer isolation.
- Still open before beta: anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, Redis failover/capacity, observability, security/accessibility hardening.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md` and `versioning.md`.