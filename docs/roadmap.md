# Дорожная карта PubChat

## Текущий статус

Released: **`0.6.5-alpha.2`**.

Current milestone: **`0.6.x-alpha`** — Pre-beta hardening продолжается.

PubChat остаётся alpha: PostgreSQL migration/recovery, Redis distributed/restart recovery, real multi-process Uvicorn/WebSocket rolling-restart, bounded slow-consumer backpressure и production deploy continuity уже закреплены CI. До beta всё ещё нужны production-like snapshot rehearsal, member-capacity/DST hardening, Redis failover/capacity, observability, load/security и финальные accessibility/operations gates.

UX-polish коммуникационных поверхностей выполняется параллельно внутри **6.7 UX/accessibility** и не заменяет следующий инфраструктурный checkpoint **6.2 Redis failover/capacity**. Production deploy hardening выполняется внутри **6.6 Operations / observability** и также не меняет порядок realtime checkpoint.

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

### 6.2 Redis / realtime reliability 🚧
- ✅ Redis 7.2 integration tests без development fallback;
- ✅ distributed ticket/presence/rate-limit/idempotency semantics;
- ✅ cross-instance pub/sub delivery;
- ✅ Redis restart/failure visibility без process-local fallback;
- ✅ command-path recovery на тех же service objects;
- ✅ automatic pub/sub resubscription после Redis restart;
- ✅ реальные multi-process Uvicorn/WebSocket scenarios;
- ✅ rolling-restart client reconnect baseline;
- ✅ slow-client/backpressure isolation;
- ⏳ Redis failover topology/capacity tests.

### 6.3 Notification worker 🚧
- ✅ baseline PostgreSQL integration smoke;
- ⏳ concurrent worker/`SKIP LOCKED` validation;
- ⏳ cursor recovery/restart tests;
- ⏳ load/idempotency profiling;
- ⏳ worker metrics/health contract.

### 6.4 Discovery / performance
- multi-source bounded candidate generation вместо newest-catalog bias;
- query/DB profiling;
- ranking latency/load tests;
- privacy/block regression под большим candidate set.

### 6.5 Security/privacy
- session/cookie/CSRF review;
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
- ⏳ structured logs/metrics/error tracking;
- ⏳ alerting/status/incident procedure;
- 🚧 deployment/recovery runbook;
- ⏳ backup retention/encryption/off-site storage + RPO/RTO policy;
- ⏳ shared/object storage;
- ⏳ expanded PostgreSQL/Redis compatibility matrix.

### 6.7 UX/accessibility
- 🚧 messaging surfaces polish v1: единый compact composer для Space chat и Messenger, встроенная attachment shelf, меньше постоянного visual chrome, desktop/mobile responsive density;
- 🚧 desktop information panels: overlay-only close controls и более компактная secondary navigation;
- ✅ authenticated bootstrap повторяет transient network/`502`/`503`/`504` сбои с bounded backoff вместо ложного окончательного outage state;
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
- Migration correctness проверяется реальной PostgreSQL.
- Backup correctness включает restore + data assertions.
- Production realtime не должен молча использовать process-local fallback.
- Redis recovery не требует process restart; ephemeral state восстанавливается протоколом, а не становится durable.
- Slow realtime consumer не должен блокировать fan-out другим соединениям.
- Production HTTP listener принадлежит process manager/systemd и не должен исчезать при routine application deploy/restart.
- Routine production deploy обновляет workers rolling reload; full application supervisor replacement не должен приводить к connection-refused на listener.
- Frontend build не очищает live SPA до успешной staged сборки и публикации assets.
- Rolling application deploy требует expand/contract-compatible schema changes на overlap window.
- Communication quality first.
- Никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
- UI/UX развивается вместе с доменной моделью.
