# PubChat version quick reference

- Current release checkpoint: **0.6.11-alpha.1** — end-to-end `account.access` platform suspension.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics, restart recovery and real Sentinel master promotion; multi-process Uvicorn/WebSocket + bounded backpressure; persistent systemd-owned production listener; message notification preferences/active-context suppression; durable unread-Messenger email delivery; Web Push/PWA Messenger delivery.
- Trust & Safety baseline: platform report intake/triage/evidence audit; explicit role authority hierarchy; Account-level capability restrictions; target-visible reasons/expiry; independent appeal queue; server-side enforcement for Messenger send, Space chat/media, Space create/join/invite, Persona edit and organic discovery publication.
- `account.access` is now fully enforced: platform-only scope, elevated permission + hierarchy checks, existing session revocation, authenticated HTTP fail-closed checks, realtime ticket re-check, distributed socket disconnect and restricted Safety/Appeal/Logout session UX.
- Moderation invariant: `Reputation != Role != Moderation Power`; Space-local moderation does not grant platform authority; a platform moderator can sanction only a lower-authority Account and only within explicit permissions.
- AI moderation invariant: AI is a copilot for triage/evidence/recommendations, not a punitive authority in the beta baseline.
- Message delivery invariant: offline external re-engagement is Messenger-only and opt-in; offline Space chat never creates background notification pressure; active context suppresses duplicate UX only and never changes authorization.
- Active next Trust & Safety task: harden moderator hierarchy/permissions and sanction authority boundaries before adding the provider-neutral AI assessment layer.
- Still open before beta: anti-spam/raid signals, moderation metrics/privacy-retention/incident rehearsal, anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, production-like load/pool profiling, observability, Safari/WebKit/security/accessibility hardening and unit-economics/monetization planning.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md`, `trust-safety-v1.md` and `versioning.md`.
