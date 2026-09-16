# PubChat version quick reference

- Current release: **0.6.8-alpha.1**.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics, restart recovery and real Sentinel master promotion; multi-process Uvicorn/WebSocket + bounded backpressure; persistent systemd-owned production listener; message notification preferences/active-context suppression; durable unread-Messenger email queue/provider/retry/lease scheduler.
- Message delivery invariant: offline external re-engagement is Messenger-only and opt-in; offline Space chat never creates background notification pressure; active context suppresses duplicate UX only and never changes authorization.
- Email delivery invariant: Account-level cooldown is not bypassed by new DM; provider execution re-checks online state, opt-in, current verified email, unread state and Account block/privacy; ledger stores no private message text or destination email.
- Active next workstream: standards-based Web Push/PWA delivery — per-device subscription lifecycle, VAPID provider, Service Worker push/click path and explicit permission UX.
- Still open before beta: anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, production-like load/pool profiling, observability, Safari/WebKit/security/accessibility hardening and Web Push gates.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md` and `versioning.md`.
