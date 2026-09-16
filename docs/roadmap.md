# Дорожная карта PubChat

## Текущий статус

Released: **`0.6.7-alpha.1`**.

Current milestone: **`0.6.x-alpha`** — Pre-beta hardening продолжается.

Уже закреплены CI: PostgreSQL migration/recovery, Redis distributed/restart recovery, real Sentinel promotion, multi-process Uvicorn/WebSocket rolling restart, bounded backpressure, production deploy continuity и message notification policy с distributed active-context suppression.

Следующий активный Stage 6.3 slice — **durable unread-Messenger email nudge**: delivery ledger, inactivity/cooldown/dedupe worker, provider abstraction и retry/backoff. После него — Web Push/PWA. До beta также остаются production-like data rehearsal, member-capacity/DST hardening, observability, load/security и browser/accessibility gates.

## Завершённые checkpoints

### Stage 1 — Foundation & Security ✅ `0.1.0-alpha.1`
Security baseline, server-side RBAC, legacy exposure fixes и CI.

### Stage 2 — Identity v2 ✅ `0.2.0-alpha.1`
Account/Persona/Credential/IdentitySession, privacy, relationships и Persona-first SPA shell.

### Stage 3 — Realtime v2 ✅ `0.3.0-alpha.1`
One-time WebSocket tickets, Redis pub/sub/presence, heartbeat/reconnect, rate limits/idempotency.

### Stage 4 — Living Spaces & Social Core ✅ `0.4.0-alpha.1`
Spaces/memberships/scoped roles, social graph, invitations, Rules/Events/History и moderation/appeals.

### Stage 5.1–5.6 ✅ `0.5.0-alpha.1` → `0.5.5-alpha.1`
Product identity/Activities, earned engagement, occurrences/reminders, cosmetic support, organic discovery и installable PWA/external reminder-worker baseline.

### Stage 6 checkpoint 1 — PostgreSQL migration baseline ✅ `0.6.0-alpha.1`
PostgreSQL 16 clean historical migration, schema-drift gate, synthetic legacy rehearsal и standalone ORM registry.

### Stage 6 checkpoint 2 — PostgreSQL recovery ✅ `0.6.1-alpha.1`
Portable dump/restore в отдельную DB с повторными Alembic/schema/data assertions.

### Stage 6 checkpoint 3 — Redis realtime ✅ `0.6.2-alpha.1`
Distributed tickets/TTL, presence, rate-limit, idempotency и cross-instance pub/sub при production semantics.

### Stage 6 checkpoint 4 — Redis restart recovery ✅ `0.6.3-alpha.1`
Real Redis outage/restart; production fail-closed; те же service objects восстанавливают commands/PubSub без process restart.

### Stage 6 checkpoint 5 — Multi-process WebSocket ✅ `0.6.4-alpha.1`
Два реальных Uvicorn process, shared Redis presence/pubsub, rolling worker restart и reconnect с новым one-time ticket.

### Stage 6 checkpoint 6 — Bounded backpressure ✅ `0.6.5-alpha.1`
Per-socket bounded outbound queue, ordering, non-blocking fan-out, queue/send-timeout slow-consumer isolation.

### Stage 6 stabilization patch ✅ `0.6.5-alpha.2`
Persistent systemd-owned listener, health-gated rolling deploy, staged SPA publish и messaging UX density pass.

### Stage 6 checkpoint 7 — Redis Sentinel failover/capacity ✅ `0.6.6-alpha.1`
Direct/Sentinel topology abstraction, real master+replica+3-Sentinel promotion rehearsal, same-service ticket/PubSub recovery и bounded concurrency до/после promotion.

### Stage 6 checkpoint 8 — Message notification policy / active context ✅ `0.6.7-alpha.1`
- account-level Messenger/Space in-app/sound preferences и opt-in flags будущих external adapters;
- Redis connection-scoped Messenger active context с TTL/heartbeat; Space active context через distributed room presence;
- duplicate toast/sound suppression, когда получатель уже смотрит тот же context, без изменения authorization;
- offline external re-engagement только для Messenger по opt-in; offline Space chat никогда не создаёт background notification pressure;
- Space alert fan-out проходит active-membership и Account-block boundaries;
- единая SPA surface для Messenger/Space alerts с существующими private/chat sounds;
- Alembic migration + preference API + deterministic policy/active-context tests;
- существующие Redis Sentinel/recovery, multi-process, deploy, PostgreSQL recovery и frontend gates остаются зелёными.

## Stage 6 — Pre-beta hardening 🚧 `0.6.x-alpha`

### 6.1 Data / migrations 🚧
- ✅ PostgreSQL 16 integration, historical clean migration, zero drift;
- ✅ synthetic legacy rehearsal и backup/restore drill;
- ⏳ anonymized production-like snapshot rehearsal;
- ⏳ member-capacity concurrency hardening;
- ⏳ IANA timezone storage и DST-correct recurring wall-clock semantics.

### 6.2 Redis / realtime reliability ✅ baseline complete
- ✅ distributed Redis semantics и production fail-closed;
- ✅ restart recovery без process restart;
- ✅ multi-process WebSocket / rolling reconnect;
- ✅ bounded slow-client isolation;
- ✅ direct/Sentinel topology, real promotion, PubSub/ticket recovery;
- ✅ bounded concurrency до/после failover.

Large-scale throughput/pool saturation остаётся в performance/observability workstream.

### 6.3 Notification worker / message delivery 🚧
- ✅ product matrix: offline external delivery только Messenger; Space alerts online-only;
- ✅ `private_notification.mp3` / `chat_notification.mp3` mapping;
- ✅ durable message preferences и deterministic policy tests;
- ✅ Redis Messenger active-context TTL + Space context через distributed presence;
- ⏳ scheduled unread-Messenger email nudge: inactivity threshold + cooldown + dedupe + opt-out;
- ⏳ durable external-delivery ledger, provider abstraction, retry/backoff;
- ⏳ Web Push adapter: Service Worker/Push API/Notifications API + VAPID + per-device lifecycle;
- ⏳ concurrent worker / `SKIP LOCKED`, restart/cursor recovery, load/idempotency;
- ⏳ delivery metrics/health и scheduler/service unit.

### 6.4 Discovery / performance 🚧
- multi-source bounded candidate generation вместо newest-catalog bias;
- query/DB profiling и ranking latency/load tests;
- privacy/block regression на большом candidate set;
- production-like realtime/Redis pool saturation profiling.

### 6.5 Security/privacy 🚧
- session/cookie/CSRF review, включая explicit CSRF proof contract;
- registration/login/refresh Safari/WebKit compatibility audit;
- upload/media review;
- moderation/report/appeal privacy audit;
- Account block coverage + privacy side-channel + secret/logging review;
- financial threat model до real payments.

### 6.6 Operations / observability 🚧
- ✅ multi-worker Uvicorn supervisor + persistent systemd socket;
- ✅ `/health/live` и dependency-aware `/health/ready`;
- ✅ health-gated rolling deploy + staged asset-first SPA publish;
- ⏳ Sentinel topology/promotion/pool metrics и alerting;
- ⏳ email delivery scheduler/service unit + provider health/metrics;
- ⏳ structured logs/error tracking, incident procedure;
- 🚧 deployment/recovery runbook;
- ⏳ backup retention/encryption/off-site storage + RPO/RTO;
- ⏳ shared/object storage и expanded compatibility matrix.

### 6.7 UX/accessibility / browser compatibility 🚧
- 🚧 compact messaging composer/density and information-panel polish;
- ✅ transient authenticated bootstrap retry;
- ✅ historical Safari registration defect audit;
- ⏳ Playwright WebKit registration/login/refresh through production-like same-origin proxy;
- ⏳ Chromium + Firefox + WebKit critical-journey matrix;
- ⏳ notification preferences UI и PWA Web Push permission/subscription UX;
- ⏳ keyboard/focus, contrast/mobile/narrow viewport, onboarding and terminology audit;
- 🚧 error/empty/offline consistency.

## Beta

Beta назначается только когда launch-critical journeys работают end-to-end, production-like gates пройдены, observability доступна и нет известных P0/P1 blockers. Ориентир `0.9.0-beta.1` не является календарным обещанием.

## Stable 1.0

`1.0.0` — первый public stable release с explicit API/data compatibility commitment.

## Постоянные инварианты

- Account != Persona.
- Reputation/achievement != Permission.
- Space moderator != Platform moderator.
- Деньги не покупают trust/moderation authority.
- Account block нельзя обойти другой Persona.
- Discovery ranking не расширяет eligibility/privacy и не покупается gift/support.
- PostgreSQL — durable source of truth; Redis — ephemeral realtime/presence/context layer.
- Production realtime не использует silent process-local fallback.
- Redis recovery/failover не требует process restart и не превращает async-replicated ephemeral state в durable guarantee.
- Slow realtime consumer не блокирует fan-out другим соединениям.
- Offline external message re-engagement относится только к Messenger и требует opt-in; Space chat не создаёт background spam отсутствующему Account.
- Active context подавляет duplicate UX, но не является authorization state.
- Notification routing не расширяет block/privacy/visibility.
- Background scheduler не запускается внутри каждого web worker.
- Service worker не является storage для auth/private API data.
- Production listener принадлежит process manager/systemd; routine deploy rolling, frontend publish staged.
- Rolling deploy требует expand/contract-compatible schema changes.
- Communication quality first; никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
