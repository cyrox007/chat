# Дорожная карта PubChat

## Текущий статус

Released: **`0.5.4-alpha.1`**.

Active development line: **`0.5.5-alpha.0`** — Web application maturity.

PubChat остаётся alpha: основные продуктовые контуры сформированы, но production-like hardening, observability/load gates и pre-beta эксплуатационные проверки ещё не завершены.

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

- bounded `ActivityOccurrence` rows и 45-day horizon;
- unique Activity+start invariant;
- monthly recurrence regression без calendar drift после короткого месяца;
- side-effect-free occurrence GET + explicit POST materialization command;
- private reminder preferences: 15m / 60m / 1d;
- максимум 200 активных reminders на Account;
- private notification inbox, unread/read/read-all;
- one reminder max per occurrence;
- explicit idempotent reconciliation/sync;
- `/activity-occurrences/v1` и `/notifications/v1`;
- reminder controls в Space Life с одним batch preferences request;
- `/notifications` screen;
- спокойный unread bell и periodic in-app sync в app shell;
- отдельный notification UX contract;
- полностью реструктурированная документация проекта.

Осознанное ограничение: recurring Activity пока UTC-anchored и не хранит IANA timezone name. DST-correct wall-clock recurrence входит в pre-beta hardening.

### Stage 5.4 — Creator Support & Cosmetic Gifts ✅ `0.5.3-alpha.1`

- opt-in Persona/Space support;
- allowlisted gifts без price/currency;
- append-only ledger + cosmetic entitlements;
- privacy/block/membership enforcement;
- sender anti-spam row-lock;
- public aggregate shelf + private received history;
- support не влияет на trust/permissions/discovery;
- Persona/Space support UI;
- no checkout/wallet/payment provider.

### Stage 5.5 — Discovery Quality ✅ `0.5.4-alpha.1`

- `/discovery/v1/spaces` отдельно от стабильного `/spaces/v1` catalog;
- eligibility/privacy/block до ranking;
- distinct recent authors вместо raw message volume;
- upcoming Activity/Event, shared topics/purpose, explicit social intent;
- private/unlisted upcoming context скрыт без active membership;
- server-only score, до трёх explainable reasons;
- bounded candidate pool + diversity pass;
- legacy rating/gifts/support/payment signals не участвуют в organic ranking.

Известное alpha-ограничение: candidate pool пока начинается с bounded canonical catalog по новизне. До beta candidate generation будет собираться из нескольких bounded источников activity/upcoming/shared context.

## Stage 5.6 — Web application maturity 🚧 `0.5.5-alpha.0`

Функциональный scope уже реализован и проходит exact-head CI; release gate ещё не завершён.

### PWA / offline shell
- локальный installable manifest и существующие 192/512 icons;
- production-only service-worker registration;
- network-first navigation shell;
- static-only runtime cache;
- API/auth/realtime/fetch-XHR responses не кэшируются;
- спокойный install prompt;
- update notice;
- PWA cache-safety regression guard.

### Notification delivery foundation
- отдельный `python -m workers.notification_reconciler`;
- scheduler не запускается в FastAPI lifecycle;
- bounded batch/max-batches;
- durable `NotificationWorkerState` cursor;
- `FOR UPDATE SKIP LOCKED` против overlap sweep;
- cursor продолжает обработку между scheduler runs и сбрасывается после конца списка;
- crash/retry безопасен благодаря notification DB dedupe.

### Frontend lifecycle
- notification unread/sync/polling вынесен в Vuex module;
- `App.vue` владеет auth/network lifecycle;
- Header только отображает unread state;
- NotificationsView обновляет единый store после read/read-all;
- authenticated bootstrap защищён от двойного запуска;
- lifecycle regression guard в CI.

### UX/accessibility
- install prompt получил named accessible region;
- update notice использует polite live region и keyboard-visible focus;
- offline copy не обещает сохранение приватных server data;
- mobile bottom-nav не расширяется PWA controls.

### Осталось до `0.5.5-alpha.1`
- docs/architecture/user guide/UI Kit sync;
- финальный exact-head CI на frozen feature head;
- version bump + CHANGELOG/version docs;
- второй exact-head CI;
- merge.

## Stage 6 — Pre-beta hardening

Обязательный gate перед beta.

### Data/migrations
- PostgreSQL integration environment;
- Redis integration tests;
- migration rehearsal на копии legacy schema/data;
- backup/restore drill;
- member-capacity concurrency hardening;
- IANA timezone storage и DST-correct recurring wall-clock semantics.

### Reliability/performance
- realtime/discovery load tests;
- DB profiling;
- Redis failure/recovery;
- slow-client/backpressure scenarios;
- notification worker/reconciliation load/idempotency tests;
- support/gift abuse-rate hardening before monetization;
- discovery candidate generation beyond newest-catalog bias.

### Security/privacy
- session/cookie/CSRF review;
- upload/media review;
- moderation/report/appeal review;
- privacy side-channel review;
- Account block coverage для всех social surfaces;
- financial threat model before any real payment provider integration.

### Operations
- structured logs/metrics/error tracking;
- reminder worker metrics/alerting;
- status/incident process;
- deployment/recovery documentation;
- shared/object storage.

### UX/accessibility
- full keyboard/focus audit;
- contrast/accessibility pass;
- mobile/narrow viewport pass;
- error/empty/offline consistency;
- onboarding usability;
- terminology audit.

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
