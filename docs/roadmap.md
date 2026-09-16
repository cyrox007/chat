# Дорожная карта PubChat

## Текущий статус

Released: **`0.6.2-alpha.1`**.

Current milestone: **`0.6.x-alpha`** — Pre-beta hardening продолжается.

PubChat остаётся alpha: основные продуктовые контуры сформированы, PostgreSQL migration/recovery baseline и Redis production-semantics integration baseline уже закреплены CI. До beta всё ещё нужны production-like snapshot rehearsal, concurrency/DST hardening, Redis restart/recovery и multi-process WebSocket tests, observability, load/security и финальные accessibility/operations gates.

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

Известное alpha-ограничение: recurring Activity пока UTC-anchored и не хранит IANA timezone name. DST-correct wall-clock recurrence входит в pre-beta hardening.

### Stage 5.4 — Creator Support & Cosmetic Gifts ✅ `0.5.3-alpha.1`
Consent-first internal gifts, append-only support ledger, cosmetic entitlements и Persona/Space support UI без real-money/payment authority.

### Stage 5.5 — Discovery Quality ✅ `0.5.4-alpha.1`
Eligibility-first organic discovery, explainable reasons, distinct-author activity signal, privacy-aware upcoming context, bounded candidate pool и no-paid/no-gift ranking boundary.

### Stage 5.6 — Web Application Maturity ✅ `0.5.5-alpha.1`
Installable PWA shell, external reminder worker, centralized notification lifecycle и PWA/cache/lifecycle regression guards.

### Stage 6 checkpoint 1 — PostgreSQL migration/integration baseline ✅ `0.6.0-alpha.1`
- PostgreSQL 16 service в backend CI;
- clean-database historical `alembic upgrade head`;
- zero model/schema drift через `alembic check`;
- synthetic representative legacy-data rehearsal с semantic assertions;
- DB URL special-character safety;
- explicit ORM registry для standalone processes;
- real async PostgreSQL smoke.

### Stage 6 checkpoint 2 — PostgreSQL recovery baseline ✅ `0.6.1-alpha.1`
- PostgreSQL 16 custom-format `pg_dump`;
- restore в отдельную database;
- restored Alembic head + zero drift;
- повторные legacy semantic assertions;
- recovery contract в `database-recovery-v1.md`.

### Stage 6 checkpoint 3 — Redis realtime baseline ✅ `0.6.2-alpha.1`
- Redis 7.2 service в backend CI;
- realtime integration smoke принудительно работает при `DEBUG=False`;
- два независимых `RealtimeService` instance используют общий distributed state;
- one-time ticket issue/consume/TTL проверяется cross-instance;
- presence register/query/unregister проверяется cross-instance;
- rate-limit counter нельзя обойти сменой worker;
- idempotency claim/release разделяется между workers;
- Redis pub/sub доставляет protocol-v2 event между независимыми instances;
- production fallback boundary закреплён документом `redis-realtime-integration-v1.md`.

## Stage 6 — Pre-beta hardening 🚧 `0.6.x-alpha`

Обязательный milestone перед beta. Новые social/product mechanics не являются приоритетом: задача — доказать корректность, переносимость и эксплуатационную готовность уже построенных контуров.

### 6.1 Data / migrations 🚧
- ✅ PostgreSQL 16 integration environment в CI;
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
- ✅ cross-instance Redis pub/sub delivery;
- ⏳ Redis restart/failure recovery без process restart;
- ⏳ потеря/восстановление pub/sub subscription;
- ⏳ реальные multi-process WebSocket scenarios;
- ⏳ slow-client/backpressure scenarios под нагрузкой;
- ⏳ reconnect после rolling restart.

### 6.3 Notification worker 🚧
- ✅ baseline integration smoke с реальным PostgreSQL и durable worker state;
- concurrent worker/`SKIP LOCKED` validation;
- cursor recovery/restart tests;
- load/idempotency profiling;
- worker metrics/health operational contract;
- подготовка delivery adapter boundary для browser/native push без включения push по умолчанию.

### 6.4 Discovery / performance
- multi-source bounded candidate generation вместо newest-catalog bias;
- query/DB profiling;
- ranking latency/load tests;
- privacy/block regression под большим candidate set;
- отсутствие paid/support influence сохраняется invariant.

### 6.5 Security/privacy
- session/cookie/CSRF review;
- upload/media validation/storage review;
- moderation/report/appeal privacy audit;
- Account block coverage по всем social surfaces;
- privacy side-channel review;
- secret/logging review;
- financial threat model до любых real payment flows.

### 6.6 Operations / observability
- structured logs;
- HTTP/realtime/worker metrics;
- error tracking;
- alerting;
- status/incident procedure;
- deployment/recovery runbook;
- backup retention/encryption/off-site storage + RPO/RTO policy;
- shared/object storage strategy;
- расширенная PostgreSQL/Redis compatibility matrix beyond current CI baselines.

### 6.7 UX/accessibility
- полный keyboard/focus audit;
- contrast/accessibility pass;
- mobile/narrow viewport pass;
- error/empty/offline consistency;
- onboarding usability;
- terminology audit;
- PWA install/update flow на Chrome/Edge/Safari-supported paths.

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
- Redis rate-limit/idempotency/presence semantics должны быть distributed.
- Synthetic fixtures не подменяют rehearsal на production-like snapshot.
- Communication quality first.
- Никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
- UI/UX развивается вместе с доменной моделью.
