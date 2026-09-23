# PubChat version quick reference

- Current release candidate: **0.6.23-alpha.1** — DST-correct recurring Activities.
- Last released `main` checkpoint: **0.6.22-alpha.2** until the final exact-head gate passes and the release candidate merges.
- Current milestone: **0.6.x-alpha** — Pre-beta hardening continues.
- Proven so far: PostgreSQL 16 migration/recovery; Redis 7.2 distributed semantics, restart recovery and real Sentinel master promotion; multi-process Uvicorn/WebSocket + bounded backpressure; persistent systemd-owned production listener; message notification preferences/active-context suppression; durable unread-Messenger email delivery; Web Push/PWA Messenger delivery.
- Trust & Safety baseline: platform report intake/triage/evidence audit; Account-level capability restrictions; target-visible reasons/expiry; independent appeal queue; full `account.access` suspension; server-side enforcement for Messenger send, Space chat/media, Space create/join/invite, Persona edit and organic discovery publication.
- Behavioral abuse signals remain advisory by default. Optional protective holds are disabled by default; when explicitly enabled they require repeated high/critical server-owned signals and can only create 5–15 minute `messenger.send` / `invitation.send` holds for non-privileged Accounts.
- AI copilot is advisory-only: privacy-minimal claimed-report evidence, bounded assessment budget, no `account.access`/permanent/revoke/appeal authority, and explicit human accepted/modified/rejected outcomes.
- Moderation power is now split by explicit server-side permissions: queue/manage access does not itself grant restriction issue, revoke or appeal-review authority; permanent restrictions and `account.access` remain elevated capabilities.
- Revocation is hierarchy-aware: an actor must outrank the target and may not directly undo a sanction issued by a higher-authority actor; permanent and `account.access` revocation keep their elevated permission checks.
- Appeal review has its own permission and requires authority at least as high as the original sanction issuer, while preserving the independent-review preference.
- Moderation invariant: `Reputation != Role != Moderation Power`; Space-local moderation does not grant platform authority; permissions and authority hierarchy are both required for punitive actions.
- AI moderation invariant: AI is a copilot for triage/evidence/recommendations, not a punitive authority in the beta baseline.
- Message delivery invariant: offline external re-engagement is Messenger-only and opt-in; offline Space chat never creates background notification pressure; active context suppresses duplicate UX only and never changes authorization.
- Reported-media moderation is human-only: quarantine/restore/remove require explicit permission, claim ownership and hierarchy checks; private evidence paths stay server-side.
- Private removed-media evidence now has bounded retention/expiry with report/appeal deferral, record-scoped deletion, metadata scrub and a standalone scheduled worker; application-level expiry does not imply forensic wipe of snapshots/backups.
- Shadow-calibration tooling is implemented, but production enforce remains closed until real human-reviewed data meets the gate and a Trust & Safety owner explicitly approves enablement; declared backup/snapshot lifecycle must also match real provider settings.
- External delivery observability now covers privacy-safe email/Web Push backlog, expired claims, retry/failure aggregates, admin metrics and a machine health CLI with structured worker completion logs.
- Browser/security gate now proves same-origin `/api`, explicit CSRF cookie+header proof, reload/refresh rotation, logout/login and non-persistent access tokens in Chromium, Firefox, WebKit and narrow mobile Chromium; production npm/pip dependency audits are mandatory.
- UI motion/loading baseline adds route/modal/popover transitions, delayed navigation progress, reduced-motion support and explicit skeleton/error/retry/pending states for core surfaces.
- Mobile routed-content hotfix wraps dynamic routes in a stable DOM transition root and requires real browser visibility assertions; session JWT issuance is collision-safe via unique `jti`.
- Space capacity admission is PostgreSQL-serialized across direct join, invitation acceptance and manager approval; concurrent final-slot activation cannot exceed `member_limit`.
- Room navigation/viewport gate now creates a real Space in browser CI, enters it through SPA navigation without reload and verifies mobile `100dvh` fit with no document-level vertical overflow.
- Recurring Activities now persist an IANA timezone and preserve local wall-clock semantics across DST, including deterministic spring-gap/fall-back handling.
- Still open before beta: accumulation of real shadow-calibration data and provider-level backup/snapshot lifecycle verification, anonymized production-like legacy snapshot rehearsal, production-like load/pool profiling, broader provider/HTTP/realtime/Redis/PostgreSQL observability, upload/privacy review, real iOS/iPadOS PWA/device testing and accessibility hardening and unit-economics/monetization planning.
- Alpha: hardening is incomplete; exact checkpoint CI is mandatory.
- Beta: launch-critical flows and production-like gates are complete; focus shifts to stabilization.
- Stable: starts at **1.0.0** after the full launch gate passes.

See `../VERSION`, `../CHANGELOG.md`, `roadmap.md`, `trust-safety-v1.md` and `versioning.md`.
