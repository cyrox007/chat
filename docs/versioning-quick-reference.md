# PubChat version quick reference

- Current release candidate: **0.6.15-alpha.1** — reversible reported-media moderation.
- Last released `main` checkpoint: **0.6.14-alpha.1** until PR #35 passes the final exact-head gate and merges.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics, restart recovery and real Sentinel master promotion; multi-process Uvicorn/WebSocket + bounded backpressure; persistent systemd-owned production listener; message notification preferences/active-context suppression; durable unread-Messenger email delivery; Web Push/PWA Messenger delivery.
- Trust & Safety baseline: platform report intake/triage/evidence audit; Account-level capability restrictions; target-visible reasons/expiry; independent appeal queue; full `account.access` suspension; server-side enforcement for Messenger send, Space chat/media, Space create/join/invite, Persona edit and organic discovery publication.
- Behavioral abuse signals are advisory evidence only: rate-limit pressure, DM distinct-recipient bursts and Space invite bursts are deduped/queued for human review and never auto-issue sanctions.
- AI copilot is advisory-only: privacy-minimal claimed-report evidence, bounded assessment budget, no `account.access`/permanent/revoke/appeal authority, and explicit human accepted/modified/rejected outcomes.
- Moderation power is now split by explicit server-side permissions: queue/manage access does not itself grant restriction issue, revoke or appeal-review authority; permanent restrictions and `account.access` remain elevated capabilities.
- Revocation is hierarchy-aware: an actor must outrank the target and may not directly undo a sanction issued by a higher-authority actor; permanent and `account.access` revocation keep their elevated permission checks.
- Appeal review has its own permission and requires authority at least as high as the original sanction issuer, while preserving the independent-review preference.
- Moderation invariant: `Reputation != Role != Moderation Power`; Space-local moderation does not grant platform authority; permissions and authority hierarchy are both required for punitive actions.
- AI moderation invariant: AI is a copilot for triage/evidence/recommendations, not a punitive authority in the beta baseline.
- Message delivery invariant: offline external re-engagement is Messenger-only and opt-in; offline Space chat never creates background notification pressure; active context suppresses duplicate UX only and never changes authorization.
- Reported-media moderation is human-only: quarantine/restore/remove require explicit permission, claim ownership and hierarchy checks; private evidence paths stay server-side.
- Active next Trust & Safety task after this checkpoint: moderation metrics/privacy-retention + incident rehearsal, then calibrated low-risk automation baseline.
- Still open before beta: moderation metrics/privacy-retention/incident rehearsal and calibrated low-risk automation, anonymized production-like legacy snapshot rehearsal, member-capacity concurrency, DST-correct recurrence, production-like load/pool profiling, observability, Safari/WebKit/security/accessibility hardening and unit-economics/monetization planning.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md`, `trust-safety-v1.md` and `versioning.md`.
