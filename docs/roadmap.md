# Дорожная карта PubChat

## Текущий статус

Released: **`0.5.5-alpha.1`**.

Next development line: **`0.6.0-alpha.0`** — Pre-beta hardening.

PubChat остаётся alpha: основные продуктовые контуры сформированы, но production-like integration, observability, load/security rehearsal и финальные accessibility/operations gates ещё не завершены.

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

Известное alpha-ограничение: candidate pool пока начинается с bounded canonical catalog по новизне. До beta candidate generation будет собираться из нескольких bounded источников activity/upcoming/shared context.

### Stage 5.6 — Web Application Maturity ✅ `0.5.5-alpha.1`

#### PWA / offline shell
- локальный installable manifest и 192/512 icons;
- production-only service-worker registration;
- network-first navigation shell;
- static-only runtime cache;
- API/auth/realtime/fetch-XHR responses не кэшируются;
- calm install/update UX;
- PWA cache-safety CI guard.

#### Notification delivery foundation
- отдельный `python -m workers.notification_reconciler`;
- scheduler не запускается в FastAPI lifecycle;
- bounded processing;
- durable `NotificationWorkerState` cursor;
- `FOR UPDATE SKIP LOCKED` против overlap sweep;
- safe retry через existing notification dedupe.

#### Frontend lifecycle
- notification state/polling вынесен в Vuex module;
- `App.vue` владеет auth/network lifecycle;
- Header presentation-only;
- NotificationsView обновляет единый unread state;
- authenticated bootstrap защищён от двойного запуска;
- lifecycle regression guard в CI.

#### UX/docs
- named install region;
- polite update live region;
- keyboard-visible focus;
- operations/system requirements/architecture/PWA UX contracts актуализированы.

Stage 5.6 не добавляет browser/native push и не обещает offline messaging/private data synchronization.

## Stage 6 — Pre-beta hardening 🚧 `0.6.0-alpha.0`

Следующий обязательный milestone перед beta. Здесь новые social/product mechanics не являются приоритетом: задача — доказать корректность, переносимость и эксплуатационную готовность уже построенных контуров.

### 6.1 Data / migrations
- поднять production-like PostgreSQL integration environment в CI;
- migration rehearsal на копии legacy schema/data;
- backup/restore drill;
- проверить Alembic upgrade from historical baseline до current head;
- member-capacity concurrency hardening;
- IANA timezone storage и DST-correct recurring wall-clock semantics.

### 6.2 Redis / realtime reliability
- Redis integration tests без development fallback;
- cross-worker realtime test environment;
- Redis restart/failure recovery;
- ticket/idempotency/presence TTL validation;
- slow-client/backpressure scenarios;
- reconnect после rolling restart.

### 6.3 Notification worker
- integration tests с реальным PostgreSQL;
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
- shared/object storage strategy;
- конкретная supported PostgreSQL/Redis compatibility matrix.

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
- Communication quality first.
- Никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
- UI/UX развивается вместе с доменной моделью.
