# Version review — 0.3.0-alpha.1

Date: 2026-09-15

This review records why the post-Stage-3 `main` branch is classified as `0.3.0-alpha.1` rather than beta or stable.

## Completed foundations

### Stage 1 — foundation/security
- server-side admin RBAC;
- profile IDOR/mass-assignment closure;
- protected user projections;
- production-safe JWT secret requirements and token-log cleanup;
- repaired database health-check;
- baseline CI.

### Stage 2 — Identity v2
- Account / Persona / Credential / IdentitySession / PrivacySettings split;
- platform roles and permissions;
- additive migration/backfill from legacy users;
- hashed canonical refresh sessions;
- Persona-first register/login/profile/privacy API;
- SPA session/bootstrap architecture and responsive app shell;
- Identity contract tests.

### Stage 3 — Realtime v2
- one-time scoped socket tickets instead of JWT in WebSocket URLs;
- Redis pub/sub and distributed presence;
- heartbeat, reconnect/resume and cross-worker delivery;
- rate limiting, message idempotency and bounded socket sends;
- server-side DM privacy/block enforcement;
- browser access token removed from persistent storage;
- Realtime contract/security regression tests and production frontend build.

## Quality evidence

The exact final Stage 3 head passed:
- backend dependency install;
- Python compile;
- FastAPI import;
- WebSocket credential regression guard;
- single Alembic head check;
- backend contract tests;
- SPA security regression guard;
- production Vite build.

## Why this is still alpha

The following launch-critical domains are incomplete or still under active redesign:
- Living Spaces canonical product model is not yet merged;
- full Space membership/request/invite UX is incomplete;
- friend/follow/block social graph needs a public API and UX;
- discovery is not yet fully relationship/privacy-aware;
- Space rules/events/history are missing;
- report/moderation/appeal audit trail is incomplete;
- production-like end-to-end and migration testing is not yet sufficient for beta;
- legacy room/user compatibility code still exists and is intentionally being retired incrementally.

## Decision

Assign `0.3.0-alpha.1` to the current `main` baseline.

Start Stage 4 as unreleased `0.4.0-alpha.0`. A beta number must not be assigned until the beta gate in `docs/versioning.md` is satisfied.
