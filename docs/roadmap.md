# Дорожная карта PubChat

## Текущий статус

Released: **`0.6.6-alpha.1`**.

Current milestone: **`0.6.x-alpha`** — Pre-beta hardening продолжается.

PubChat остаётся alpha: PostgreSQL migration/recovery, Redis distributed/restart recovery, real Sentinel master promotion, real multi-process Uvicorn/WebSocket rolling-restart, bounded slow-consumer backpressure и production deploy continuity уже закреплены CI. До beta всё ещё нужны production-like snapshot rehearsal, member-capacity/DST hardening, observability, load/security, message delivery hardening и финальные accessibility/browser/operations gates.

Redis failover/capacity baseline завершён checkpoint `0.6.6-alpha.1`. Следующий активный product/infrastructure workstream — **6.3 Notification worker / message delivery**: online/offline notification policy, active-context suppression, unread-Messenger email nudge и затем Web Push. UX/browser/security work идёт параллельно внутри 6.5–6.7.

## Завершённые checkpoints

### Stage 1 — Foundation & Security ✅ `0.1.0-alpha.1`
Security baseline, server-side RBAC, legacy data exposure fixes и CI.

### Stage 2 — Identity v2 ✅ `0.2.0-alpha.1`
Account/Persona/Credential/IdentitySession, privacy, relationships, Persona-first onboarding и SPA shell.

### Stage 3 — Realtime v2 ✅ `0.3.0-alpha.1`
One-time WebSocket tickets, Redis pub/sub/presence, multi-worker delivery, heartbeat/reconnect, rate limits/idempotency и memory-only access JWT.

### Stage 4 — Living Spaces & Social Core ✅ `0.4.0-alpha.1`
Canonical Spaces/memberships/scoped roles, social graph, privacy-aware discovery, invitations, Rules/Events/History и transparent moderation/appeals.

### Stage 5.1 — Product Identity & Activities ✅ `0.5.0-alpha.1`
Persona/Space Appearance, recurring Activities, RSVP, `next_starts_at` и mobile-first customization/activity UI.

### Stage 5.2 — Social Engagement ✅ `0.5.1-alpha.1`
Earned achievements и Conversation Rounds без score/winner/prize/stake, интегрированные с block/membership/scoped roles.

### Stage 5.3 — Activity Occurrences & Notifications ✅ `0.5.2-alpha.1`
Bounded occurrences, opt-in reminders, private notification inbox, idempotent reconciliation и notification UX.

### Stage 5.4 — Creator Support & Cosmetic Gifts ✅ `0.5.3-alpha.1`
Consent-first internal gifts, append-only support ledger, cosmetic entitlements и Persona/Space support UI без real-money/payment authority.

### Stage 5.5 — Discovery Quality ✅ `0.5.4-alpha.1`
Eligibility-first organic discovery, explainable reasons, privacy-aware ranking и no-paid/no-gift ranking boundary.

### Stage 5.6 — Web Application Maturity ✅ `0.5.5-alpha.1`
Installable PWA shell, external reminder worker, centralized notification lifecycle и regression guards.

### Stage 6 checkpoint 1 — PostgreSQL migration/integration baseline ✅ `0.6.0-alpha.1`
PostgreSQL 16 clean historical migration, zero drift, synthetic legacy rehearsal, async smoke и standalone ORM registry.

### Stage 6 checkpoint 2 — PostgreSQL recovery baseline ✅ `0.6.1-alpha.1`
Portable custom-format dump/restore в отдельную DB с повторными Alembic/schema/data assertions.

### Stage 6 checkpoint 3 — Redis realtime baseline ✅ `0.6.2-alpha.1`
Redis 7.2 при `DEBUG=False`: distributed tickets/TTL, presence, rate-limit, idempotency и cross-instance pub/sub.

### Stage 6 checkpoint 4 — Redis restart recovery ✅ `0.6.3-alpha.1`
- CI реально останавливает Redis 7.2 service container;
- outage в production semantics возвращает `RealtimeUnavailable` и не включает local fallback;
- тот же Redis container запускается снова;
- те же `RealtimeService` objects восстанавливают ticket issue/consume без process restart;
- pub/sub listener автоматически пересоздаёт subscription после restart;
- test cleanup гарантированно возвращает Redis в рабочее состояние;
- PostgreSQL migration/recovery и frontend gates продолжают проходить в том же pipeline.

### Stage 6 checkpoint 5 — Multi-process WebSocket / rolling restart ✅ `0.6.4-alpha.1`
- CI поднимает два отдельных Uvicorn/FastAPI process против общих PostgreSQL и Redis;
- one-time tickets consume-ятся worker process через production WebSocket auth path;
- distributed presence и Redis pub/sub проверяются между process boundaries;
- один worker останавливается, пока второй продолжает обслуживать realtime traffic;
- replacement worker принимает reconnect с новым one-time ticket;
- существующие PostgreSQL/Redis recovery и frontend gates остаются зелёными.

### Stage 6 checkpoint 6 — Bounded WebSocket backpressure ✅ `0.6.5-alpha.1`
- каждый local WebSocket имеет отдельную bounded outbound queue;
- Redis/pub/sub callback только enqueue-ит frame и не ждёт медленный network write;
- один sender task на socket сохраняет порядок сообщений;
- `queue_full` и `send_timeout` изолированно отключают slow consumer с code `1013`;
- queue capacity configurable через `REALTIME_OUTBOUND_QUEUE_SIZE`;
- deterministic tests подтверждают ordering, non-blocking overflow и timeout isolation;
- multi-process/recovery/backup/frontend gates остаются зелёными.

### Stage 6 stabilization patch — Deploy continuity & messaging UX ✅ `0.6.5-alpha.2`
- production listener принадлежит systemd socket unit и остаётся bound при замене Uvicorn supervisor;
- production Uvicorn работает минимум с двумя workers и routine deploy использует `SIGHUP` rolling reload;
- `/health/live` и `/health/ready` дают liveness/dependency readiness contract;
- CI проверяет HTTP continuity как при worker reload, так и при полном supervisor replacement за persistent inherited socket;
- frontend строится staged и публикует `index.html` только после assets, не очищая live SPA во время build;
- authenticated bootstrap повторяет transient network/`502`/`503`/`504` ошибки;
- Space chat/Messenger получили compact composer, attachment shelf и первый density/interaction polish pass.

### Stage 6 checkpoint 7 — Redis Sentinel failover/capacity baseline ✅ `0.6.6-alpha.1`
- direct `REDIS_URL` mode сохранён backward-compatible;
- добавлен Redis Sentinel topology mode с discovery актуального master;
- master и Sentinel authentication/configuration разделены;
- production realtime не включает local fallback при failover;
- CI поднимает master, replica и три Sentinel process с quorum `2`;
- master реально останавливается, replica автоматически promotes;
- те же `RealtimeService` objects восстанавливают ticket issue/consume без restart application process;
- PubSub listener пересоздаёт subscription через promoted master;
- bounded concurrent ticket bursts проходят до и после promotion;
- restart recovery, multiprocess WebSocket, rolling deploy, PostgreSQL migration/recovery и frontend gates остаются зелёными.

## Stage 6 — Pre-beta hardening 🚧 `0.6.x-alpha`

### 6.1 Data / migrations 🚧
- ✅ PostgreSQL 16 integration environment;
- ✅ historical clean migration chain;
- ✅ zero model/schema drift;
- ✅ synthetic representative legacy-data rehearsal;
- ✅ PostgreSQL backup/restore recovery drill;
- ⏳ rehearsal на anonymized production-like snapshot;
- ⏳ member-capacity concurrency hardening;
- ⏳ IANA timezone storage и DST-correct recurring wall-clock semantics.

### 6.2 Redis / realtime reliability ✅ baseline complete
- ✅ Redis 7.2 integration tests без development fallback;
- ✅ distributed ticket/presence/rate-limit/idempotency semantics;
- ✅ cross-instance pub/sub delivery;
- ✅ Redis restart/failure visibility без process-local fallback;
- ✅ command-path recovery на тех же service objects;
- ✅ automatic pub/sub resubscription после Redis restart;
- ✅ реальные multi-process Uvicorn/WebSocket scenarios;
- ✅ rolling-restart client reconnect baseline;
- ✅ slow-client/backpressure isolation;
- ✅ direct/Sentinel topology abstraction с backward-compatible `REDIS_URL` mode;
- ✅ real Redis Sentinel master/replica promotion rehearsal без restart application process;
- ✅ PubSub resubscription и ticket semantics после promotion;
- ✅ bounded connection/ticket concurrency до и после failover.

Дальнейшие large-scale throughput/load benchmarks относятся к 6.4/6.6 performance/observability и не блокируют сам failover correctness checkpoint.

### 6.3 Notification worker / message delivery 🚧
- ✅ baseline PostgreSQL integration smoke;
- ✅ product delivery contract: offline external notifications относятся только к Messenger/direct messages; Space chat notifications разрешены, когда Account online;
- ✅ существующие sound assets зафиксированы как `private_notification.mp3` для Messenger и `chat_notification.mp3` для Space chat;
- 🚧 durable message-notification preferences и policy tests для online/offline/active-context matrix;
- ⏳ Redis active-context TTL (`messenger:<dialog>`, `space:<room>`) для подавления дублирующего toast/sound, когда пользователь уже смотрит тот же context;
- ⏳ scheduled unread-Messenger email nudge для давно отсутствующих Accounts: inactivity threshold + cooldown + dedupe + opt-out, без письма на каждое сообщение;
- ⏳ durable external-delivery ledger, retry/backoff и provider abstraction;
- ⏳ Web Push adapter поверх Service Worker/Push API/Notifications API с VAPID и per-device subscription lifecycle;
- ⏳ concurrent worker/`SKIP LOCKED` validation;
- ⏳ cursor recovery/restart tests;
- ⏳ load/idempotency profiling;
- ⏳ worker/delivery metrics и health contract.

### 6.4 Discovery / performance
- multi-source bounded candidate generation вместо newest-catalog bias;
- query/DB profiling;
- ranking latency/load tests;
- privacy/block regression под большим candidate set;
- production-like realtime/Redis pool saturation profiling сверх bounded failover correctness test.

### 6.5 Security/privacy
- session/cookie/CSRF review, включая явный CSRF proof contract вместо неявной зависимости от browser cookie behavior;
- registration/login/refresh cookie compatibility audit для Safari/WebKit;
- upload/media review;
- moderation/report/appeal privacy audit;
- Account block coverage audit;
- privacy side-channel review;
- secret/logging review;
- financial threat model до real payments.

### 6.6 Operations / observability
- ✅ production Uvicorn supervisor: минимум два worker при `DEBUG=False`, development reload только при `DEBUG=True`;
- ✅ systemd-owned persistent listener `127.0.0.1:9000` переживает application supervisor restart;
- ✅ tracked systemd service с `Restart=always` и `SIGHUP` rolling reload вместо routine full restart;
- ✅ `/health/live` и dependency-aware `/health/ready` для PostgreSQL + production Redis;
- ✅ health-gated deploy script и отдельный one-time installer для перехода с legacy service;
- ✅ staged SPA publish не очищает текущий live build и переключает `index.html` последним;
- ✅ CI rehearsal подтверждает HTTP continuity при SIGHUP и при полном supervisor replacement за persistent socket;
- ⏳ Sentinel topology/promotion/pool metrics и alerting;
- ⏳ email delivery scheduler/service unit и provider health/metrics;
- ⏳ structured logs/metrics/error tracking;
- ⏳ alerting/status/incident procedure;
- 🚧 deployment/recovery runbook;
- ⏳ backup retention/encryption/off-site storage + RPO/RTO policy;
- ⏳ shared/object storage;
- ⏳ expanded PostgreSQL/Redis compatibility matrix.

### 6.7 UX/accessibility / browser compatibility 🚧
- 🚧 messaging surfaces polish v1: единый compact composer для Space chat и Messenger, встроенная attachment shelf, меньше постоянного visual chrome, desktop/mobile responsive density;
- 🚧 desktop information panels: overlay-only close controls и более компактная secondary navigation;
- ✅ authenticated bootstrap повторяет transient network/`502`/`503`/`504` сбои с bounded backoff вместо ложного окончательного outage state;
- ✅ исторический Safari registration audit: ранняя версия зависела от cookie-only CSRF handshake и могла ломаться при cross-site cookie blocking; отдельный mount-time CSRF fetch также создавал race window;
- ⏳ Playwright WebKit registration/login/refresh smoke через production-like same-origin proxy;
- ⏳ Chromium + Firefox + WebKit critical-journey browser matrix;
- ⏳ PWA Web Push permission/subscription UX; iOS/iPadOS installed Home Screen flow включается в device/browser matrix;
- ⏳ notification preferences UI: Messenger/Space sound, email unread-DM nudge, Web Push;
- ⏳ полный keyboard/focus audit;
- ⏳ contrast/mobile/narrow viewport pass;
- 🚧 error/empty/offline consistency;
- ⏳ onboarding usability;
- ⏳ terminology audit;
- ⏳ PWA install/update browser matrix.

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
- Discovery ranking не расширяет eligibility/privacy.
- Organic discovery нельзя купить через gift/support.
- Service worker не является storage для auth/private API data.
- Background scheduler не запускается внутри каждого web worker.
- Offline external message re-engagement относится только к Messenger; Space chat не создаёт фоновый notification spam отсутствующему Account.
- Message notification routing не расширяет block/privacy/visibility.
- Migration correctness проверяется реальной PostgreSQL.
- Backup correctness включает restore + data assertions.
- Production realtime не должен молча использовать process-local fallback.
- Redis recovery/failover не требует process restart; ephemeral state восстанавливается протоколом, а не становится durable.
- Redis Sentinel promotion не превращает async-replicated ephemeral keys/pub-sub в durable delivery guarantee.
- Slow realtime consumer не должен блокировать fan-out другим соединениям.
- Production HTTP listener принадлежит process manager/systemd и не должен исчезать при routine application deploy/restart.
- Routine production deploy обновляет workers rolling reload; full application supervisor replacement не должен приводить к connection-refused на listener.
- Frontend build не очищает live SPA до успешной staged сборки и публикации assets.
- Rolling application deploy требует expand/contract-compatible schema changes на overlap window.
- Communication quality first.
- Никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
- UI/UX развивается вместе с доменной моделью.
