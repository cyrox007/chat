# PubChat version quick reference

- Current release: **0.6.7-alpha.1**.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics, restart recovery and real Sentinel master promotion; PubSub/ticket recovery on the same service objects after promotion; real multi-process Uvicorn/WebSocket delivery; rolling-restart reconnect with fresh one-time tickets; bounded per-socket outbound queues with slow-consumer isolation; persistent systemd-owned production listener; message notification preferences with online/offline routing and distributed active-context suppression.
- Message delivery invariant: offline external re-engagement is Messenger-only and opt-in; offline Space chat never creates background notification pressure; active context suppresses duplicate UX only and never changes authorization.
- Active next workstream: durable unread-Messenger email nudge — delivery ledger, inactivity/cooldown/dedupe worker, provider abstraction and retry/backoff; Web Push/PWA follows.
- Still open before beta: anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, production-like load/pool profiling, observability, security/browser/accessibility hardening and external notification delivery gates.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md` and `versioning.md`.
