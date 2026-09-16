# PubChat version quick reference

- Current release: **0.6.2-alpha.1**.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery gates plus Redis 7.2 distributed realtime semantics at `DEBUG=False` (tickets, TTL, presence, rate-limit, idempotency, pub/sub).
- Still open before beta: anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, Redis restart/recovery and multi-process WebSocket scenarios, observability, load/security/accessibility hardening.
- Alpha: product/hardening work is still incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION` for the released number, `../CHANGELOG.md` for release history, `roadmap.md` for active work and `versioning.md` for policy.
