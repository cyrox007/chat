# Дорожная карта PubChat

## Текущий статус

Released: **`0.6.9-alpha.1`**.

Current milestone: **`0.6.x-alpha`** — Pre-beta hardening продолжается.

Уже закреплены CI: PostgreSQL migration/recovery, Redis distributed/restart recovery, real Sentinel promotion, multi-process Uvicorn/WebSocket rolling restart, bounded backpressure, production deploy continuity, message notification policy с distributed active-context suppression, durable unread-Messenger email delivery и Web Push/PWA Messenger delivery.

Следующий launch-critical workstream — **production-grade moderation / Trust & Safety**: единый report flow, moderator queue, evidence boundaries, scoped actions, audit trail и appeals end-to-end. Параллельно продолжаются delivery observability/browser matrix, security gates и формализация unit economics/monetization boundaries.

Отдельно зафиксированы два обязательных launch workstream, которые раньше были недооценены: **production-grade moderation / Trust & Safety** и **устойчивая монетизация / unit economics**. Текущий Report/ModerationAction/Appeal foundation полезен, но сам по себе не является готовой операционной системой модерации. PubChat также не может рассчитывать, что инфраструктура, поддержка и Trust & Safety будут бесконечно финансироваться только энтузиазмом команды.

## Завершённые checkpoints

### Stage 1 — Foundation & Security ✅ `0.1.0-alpha.1`
Security baseline, server-side RBAC, legacy exposure fixes и CI.

### Stage 2 — Identity v2 ✅ `0.2.0-alpha.1`
Account/Persona/Credential/IdentitySession, privacy, relationships и Persona-first SPA shell.

### Stage 3 — Realtime v2 ✅ `0.3.0-alpha.1`
One-time WebSocket tickets, Redis pub/sub/presence, heartbeat/reconnect, rate limits/idempotency.

### Stage 4 — Living Spaces & Social Core ✅ `0.4.0-alpha.1`
Spaces/memberships/scoped roles, social graph, invitations, Rules/Events/History и moderation/appeals foundation.

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
- account-level Messenger/Space in-app/sound preferences и opt-in flags external adapters;
- Redis connection-scoped Messenger active context с TTL/heartbeat; Space active context через distributed room presence;
- duplicate toast/sound suppression, когда получатель уже смотрит тот же context, без изменения authorization;
- offline external re-engagement только для Messenger по opt-in; offline Space chat никогда не создаёт background notification pressure;
- Space alert fan-out проходит active-membership и Account-block boundaries;
- единая SPA surface для Messenger/Space alerts с существующими private/chat sounds;
- Alembic migration + preference API + deterministic policy/active-context tests.

### Stage 6 checkpoint 9 — Durable unread-Messenger email delivery ✅ `0.6.8-alpha.1`
- durable privacy-minimal external delivery ledger без private message body и destination email;
- scheduled inactivity/cooldown/dedupe candidate worker только для opt-in Messenger re-engagement;
- current online presence, verified email, unread state и Account block/privacy повторно проверяются непосредственно перед delivery;
- новые DM не обходят Account-level email cooldown;
- SMTP provider поддерживает STARTTLS/implicit SSL, stable Message-ID и privacy-safe aggregate template;
- retryable/terminal provider failures разделены, retries используют bounded exponential backoff;
- delivery records claim-ятся через `FOR UPDATE SKIP LOCKED` + expiring lease; expired claim recoverable после crash;
- worker берёт по одному delivery claim непосредственно перед network send, чтобы batch не создавал преждевременный lease expiry;
- systemd oneshot/timer и installer выносят scheduler из FastAPI worker lifecycle;
- PostgreSQL integration test фиксирует concurrent disjoint claims + expired-lease recovery;
- legacy Messenger/Space User UID явно сопоставляется с Account через `legacy_user_uid`, Account block/privacy не смешивается с legacy identity.

### Stage 6 checkpoint 10 — Web Push / PWA Messenger delivery ✅ `0.6.9-alpha.1`
- Account-owned per-device PushSubscription model с endpoint fingerprinting и explicit register/status/remove lifecycle;
- VAPID provider: private key backend-only, SPA получает только public key/capability;
- browser notification permission запрашивается только после явного user gesture и никогда не появляется на bootstrap;
- offline Web Push queue создаётся только для Messenger; offline Space chat по-прежнему не создаёт external re-engagement pressure;
- privacy-minimal push payload не содержит private message body или sender identity и открывает только same-origin Messenger route;
- Redis presence, opt-in, unread state и Account block/privacy повторно проверяются перед provider send;
- общий `external_delivery_ledger` используется для Web Push с per-conversation cooldown/dedupe, `FOR UPDATE SKIP LOCKED`, expiring lease и bounded retry/backoff;
- terminal provider responses `404/410` удаляют протухшие subscriptions;
- отдельный systemd worker/timer выносит delivery из Uvicorn lifecycle;
- service worker получил push/click flow без расширения static-only cache boundary;
- logout/session teardown отвязывает local push subscription best-effort для shared-browser safety;
- Notifications UI получил email/Web Push controls; deterministic provider/privacy/PWA guards закреплены в CI.

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
- ✅ scheduled unread-Messenger email nudge: inactivity threshold + Account cooldown + dedupe + opt-out;
- ✅ durable external email ledger + SMTP provider + retry/backoff + expiring claim lease;
- ✅ concurrent worker / `SKIP LOCKED` claim validation и expired-lease recovery;
- ✅ external email scheduler/service unit вне web-worker lifecycle;
- ✅ Web Push adapter: Service Worker/Push API/Notifications API + VAPID + per-device subscription lifecycle;
- ✅ terminal push subscription cleanup + retry/backoff integration;
- ✅ notification preferences UI для email/Web Push;
- ⏳ delivery metrics/health, load/idempotency profiling.

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
- ✅ external Messenger email systemd scheduler/service + fail-fast provider config installer;
- ✅ external Messenger Web Push systemd scheduler/service + VAPID preflight installer;
- ⏳ Sentinel topology/promotion/pool metrics и alerting;
- ⏳ email/push delivery metrics/provider health;
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
- ✅ notification preferences UI и baseline PWA Web Push permission/subscription UX;
- ⏳ iOS/iPadOS installed Home Screen push flow в device/browser matrix;
- ⏳ keyboard/focus, contrast/mobile/narrow viewport, onboarding and terminology audit;
- 🚧 error/empty/offline consistency.

### 6.8 Trust & Safety / moderation launch readiness 🚧

Stage 4 дал доменные сущности reports/actions/appeals, но **production-grade moderation пока не готова**. До публичного запуска нужен не только schema/API foundation, а рабочий операционный контур.

- ⏳ единый пользовательский report flow из Persona, Messenger message, Space message, Space/profile и media attachment;
- ⏳ report reason taxonomy, severity/priority, duplicate collapse и rate-limit против report spam;
- ⏳ moderator queue с фильтрами, search, ownership/claim, priority и состояниями triage/in-review/resolved/escalated;
- ⏳ безопасный evidence snapshot/reference: что именно было пожаловано, контекст, timestamps и минимально необходимая история без бесконтрольного доступа к приватной переписке;
- ⏳ platform moderation actions по Account/content с чётким scope, сроком, reason code и human-readable explanation;
- ⏳ Space-local moderation отдельно от platform Trust & Safety; Space moderator не получает глобальных прав;
- ⏳ Account-level block/suspension/ban-evasion enforcement для sibling Persona и новых Persona того же Account;
- ⏳ anti-spam/raid baseline: message burst, invite/DM abuse, repeated unsolicited contacts, mass-join/leave и очевидная automation pressure;
- ⏳ media/upload abuse workflow: quarantine/remove/review hooks без автоматической выдачи модератору лишних приватных данных;
- ⏳ immutable/auditable moderation history, actor/reason/scope/duration и защита от тихого редактирования прошлых решений;
- ⏳ полноценная appeal queue, повторная проверка другим moderator/admin там, где это уместно, и защита от бесконечного appeal spam;
- ⏳ internal moderator UX: быстрый context review, linked reports/history, но без публичного social score и без автоматического «вердикта» на основе reputation;
- ⏳ moderation metrics: queue age, response time, action/appeal counts, overturned decisions, abuse-rate signals; без KPI, стимулирующих модераторов выдавать больше санкций;
- ⏳ privacy/retention policy для reports/evidence и redaction/export procedures;
- ⏳ load/incident rehearsal: spam-wave/raid, moderator backlog, Redis/backend outage во время incident response.

**Beta gate:** нельзя считать модерацию готовой только потому, что `Report`, `ModerationAction` и `Appeal` существуют в БД. Для публичной beta должен работать end-to-end flow «пожаловаться → очередь → решение → аудит → уведомление → апелляция» хотя бы для основных типов abuse.

### 6.9 Sustainable monetization / business viability 🚧

Цель — финансировать инфраструктуру, storage/traffic, email/push, поддержку и Trust & Safety без продажи trust, moderation authority или organic ranking.

- ⏳ построить cost model: PostgreSQL/Redis/compute, storage, egress/CDN, uploads/media, email, push, backups, observability, support/moderation; считать cost per active Account / message / stored GB там, где метрика полезна;
- ⏳ определить минимальный monthly revenue target: infrastructure + moderation/support + payment/provider fees + safety reserve, а не только «сервер пока оплачивается»;
- ⏳ выбрать 1–2 monetization hypotheses для beta и не распыляться на полноценную игровую экономику;
- ⏳ основной кандидат — PubChat Plus: косметика/темы, расширенное оформление Persona/Space, дополнительные convenience-функции и разумные resource limits без деградации базового общения;
- ⏳ отдельный cosmetic catalog / gifts / Space appearance entitlements, не влияющие на trust, permissions, moderation или discovery ranking;
- ⏳ проверить модель дополнительных storage/media limits для платных Account/Space, сохраняя бесплатный базовый messaging path;
- ⏳ позже проверить real creator/Space support с прозрачной комиссией платформы; это отдельный financial/security/legal checkpoint, не продолжение текущих бесплатных cosmetic gestures;
- ⏳ исследовать professional/community plan для управляемых Spaces: дополнительные admin/analytics/storage инструменты, но без покупки места в organic discovery;
- ⏳ entitlement model server-side: subscription/cosmetic/resource entitlement отдельно от Account trust, role и permissions;
- ⏳ pricing/retention experiments: conversion, churn, ARPPU/ARPU и willingness-to-pay без dark patterns, искусственных streak losses и давления через личные сообщения;
- ⏳ payment provider, receipts/refunds/chargebacks, tax/legal/privacy requirements и fraud controls до первого real-money transaction;
- ⏳ observability для revenue pipeline без хранения лишних платёжных данных в PubChat;
- ⏳ зафиксировать бесплатное ядро продукта и платные границы до beta, чтобы monetization не переделывала архитектуру после роста.

**Жёсткие ограничения монетизации:** деньги не покупают trust, verification-as-authority, moderation immunity, Space/platform moderator role, обход block/privacy/rate-limit, преимущество в organic discovery или право сильнее воздействовать на других пользователей. Appeals/reporting/security recovery также не становятся платными функциями.

## Beta

Beta назначается только когда launch-critical journeys работают end-to-end, production-like gates пройдены, observability доступна и нет известных P0/P1 blockers. Помимо technical reliability, до публичной beta должен существовать рабочий moderation/Trust & Safety контур и понятная операционная модель его поддержки. Monetization может не быть полностью включена в первой beta, но до расширения аудитории должны быть выбраны monetization hypothesis, cost model и бесплатные/платные границы продукта, чтобы инфраструктура и moderation не зависели от бессрочного ручного финансирования.

Ориентир `0.9.0-beta.1` не является календарным обещанием.

## Stable 1.0

`1.0.0` — первый public stable release с explicit API/data compatibility commitment, рабочей moderation operations model и устойчивым планом финансирования инфраструктуры/поддержки.

## Постоянные инварианты

- Account != Persona.
- Reputation/achievement != Permission.
- Space moderator != Platform moderator.
- Деньги не покупают trust/moderation authority.
- Платный entitlement не расширяет privacy/access/abuse permissions.
- Account block нельзя обойти другой Persona.
- Discovery ranking не расширяет eligibility/privacy и не покупается gift/support.
- PostgreSQL — durable source of truth; Redis — ephemeral realtime/presence/context layer.
- Production realtime не использует silent process-local fallback.
- Redis recovery/failover не требует process restart и не превращает async-replicated ephemeral state в durable guarantee.
- Slow realtime consumer не блокирует fan-out другим соединениям.
- Offline external message re-engagement относится только к Messenger и требует opt-in; Space chat не создаёт background spam отсутствующему Account.
- Active context подавляет duplicate UX, но не является authorization state.
- Notification routing не расширяет block/privacy/visibility.
- External delivery ledger не хранит private message text или destination email.
- Web Push payload не хранит/не раскрывает private message body или sender identity; VAPID private key остаётся server-only.
- Background scheduler не запускается внутри каждого web worker.
- Service worker не является storage для auth/private API data.
- Production listener принадлежит process manager/systemd; routine deploy rolling, frontend publish staged.
- Rolling deploy требует expand/contract-compatible schema changes.
- Moderation decision имеет scope/reason/audit trail и не покупается за деньги.
- Communication quality first; никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
