# PubChat version quick reference

- Current release: **0.6.1-alpha.1**.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: clean PostgreSQL 16 migration chain, zero `alembic check` drift, async PostgreSQL smoke, synthetic representative legacy-data rehearsal and executable PostgreSQL backup/restore with repeated schema/data assertions.
- Still open before beta: anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, Redis/realtime reliability, observability, load/security/accessibility hardening.
- Alpha: product/hardening work is still incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION` for the released number, `../CHANGELOG.md` for release history, `roadmap.md` for active work and `versioning.md` for policy.
