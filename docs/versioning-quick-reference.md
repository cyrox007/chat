# PubChat version quick reference

- Current release candidate: **0.6.10-alpha.1** (PR #30; not released until exact-head CI and merge are complete).
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics, restart recovery and real Sentinel master promotion; multi-process Uvicorn/WebSocket + bounded backpressure; persistent systemd-owned production listener; message notification preferences/active-context suppression; durable unread-Messenger email delivery; Web Push/PWA Messenger delivery.
- Trust & Safety checkpoint: platform report intake/triage/evidence audit; explicit role authority hierarchy; Account-level capability restrictions; target-visible reasons/expiry; independent appeal queue; server-side enforcement for Messenger send, Space chat/media, Space create/join/invite, Persona edit and organic discovery publication.
- Moderation invariant: `Reputation != Role != Moderation Power`; Space-local moderation does not grant platform authority; a platform moderator can sanction only a lower-authority Account and only within explicit permissions.
- AI moderation invariant: AI is a copilot for triage/evidence/recommendations, not a punitive authority in the beta baseline.
- `account.access` remains intentionally non-issuable until session revocation, HTTP/realtime enforcement and Safety/Appeal/Logout exception paths are implemented end-to-end.
- Message delivery invariant: offline external re-engagement is Messenger-only and opt-in; offline Space chat never creates background notification pressure; active context suppresses duplicate UX only and never changes authorization.
- Active next Trust & Safety work after this checkpoint: full Account access suspension semantics, AI assessment storage/provider-neutral adapter, anti-spam/raid signals, moderation metrics/privacy-retention and incident rehearsal.
- Still open before beta: anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, production-like load/pool profiling, observability, Safari/WebKit/security/accessibility hardening and remaining Trust & Safety gates.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md`, `trust-safety-v1.md` and `versioning.md`.
