# PubChat version quick reference

- Current release: **0.6.0-alpha.1**.
- Current development line: **0.6.0-alpha.x** — Pre-beta hardening continues.
- Proven in this checkpoint: clean PostgreSQL 16 migration chain, zero `alembic check` drift, backend contract tests and async PostgreSQL smoke.
- Still open before beta: representative legacy-data rehearsal, backup/restore, concurrency/DST work, Redis/realtime reliability, observability, load/security/accessibility hardening.
- Alpha: product/hardening work is still incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION` for the released number, `../CHANGELOG.md` for release history, `roadmap.md` for active work and `versioning.md` for policy.
