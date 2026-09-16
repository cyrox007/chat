# PubChat version quick reference

- Current release: **0.6.6-alpha.1**.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics, restart recovery and real Sentinel master promotion; PubSub/ticket recovery on the same service objects after promotion; real multi-process Uvicorn/WebSocket delivery; rolling-restart reconnect with fresh one-time tickets; bounded per-socket outbound queues with slow-consumer isolation; persistent systemd-owned production listener, health-gated rolling deploy and staged SPA publish.
- Active next workstream: notification/message delivery hardening — online/offline routing, active-context suppression, unread-Messenger email nudge, delivery ledger and Web Push/PWA adapter.
- Still open before beta: anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, production-like load/pool profiling, observability, security/browser/accessibility hardening and notification delivery gates.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md` and `versioning.md`.
