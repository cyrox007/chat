# Дорожная карта PubChat

## Текущий статус

Released: **`0.5.4-alpha.1`**.

Next development line: **`0.5.5-alpha.0`** — Web application maturity.

PubChat остаётся alpha: основные продуктовые контуры сформированы, но production-like hardening, web/PWA maturity и pre-beta эксплуатационные проверки ещё не завершены.

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

Browser/native push не входит в `0.5.2`; domain inbox и reconciliation теперь являются базой для будущего delivery adapter.

### Stage 5.4 — Creator Support & Cosmetic Gifts ✅ `0.5.3-alpha.1`

- opt-in `CreatorSupportProfile` для Persona;
- opt-in `SpaceSupportSettings` для Spaces;
- allowlisted `GiftDefinition` catalog без price/currency;
- append-only `SupportLedgerEntry` с snapshot labels;
- `CosmeticEntitlement`, отделённый от permissions/trust/reputation;
- Persona gifts соблюдают profile privacy + Account-level block;
- Space gifts требуют active membership;
- self-gift Persona запрещён;
- owner не может отправлять gift собственному Space;
- максимум 20 внутренних gifts с Account за rolling 24h;
- sender limit сериализован Account row lock против concurrent bypass;
- публичный shelf показывает только gift + aggregate count;
- sender/message доступны только recipient/manager private history;
- historical ledger переживает удаление Persona/Space через `SET NULL` live references + snapshots;
- `/support/v1` contract;
- Persona opt-in/history встроены в «Стиль образа»;
- support shelf + gift picker встроены в Persona profile;
- отдельный `/spaces/:uid/support` с Space shelf, gift flow и manager settings/history;
- contract regressions запрещают payment/balance/price/power fields и ledger mutation routes.

`0.5.3` остаётся бесплатным/internal support slice. Реальные payments требуют отдельного financial/security review и transaction/fraud/idempotency модели.

### Stage 5.5 — Discovery Quality ✅ `0.5.4-alpha.1`

- новый `/discovery/v1/spaces`; стабильный `/spaces/v1` catalog не сломан;
- eligibility/privacy применяется до ranking;
- Account-level block подавляет новую owner-led публичную рекомендацию;
- недавняя активность считается по разным авторам, а не raw message volume;
- учитываются upcoming Activity/Event, shared topics/purpose, explicit social intent, modest freshness/member-count context;
- private/unlisted Space без active membership не раскрывает внутренний upcoming context;
- server-only score не входит в API;
- до трёх объяснимых причин «Почему здесь»;
- bounded candidate pool до 200 Spaces;
- diversity pass уменьшает однообразие purpose без обхода filters/privacy;
- legacy `Room.rating`, gifts/support, price/currency/payment не участвуют в ranking;
- SPA Discovery переведён на новый endpoint и показывает reasons + nearest allowed upcoming item;
- отдельные domain и UX contracts для organic discovery.

Известное alpha-ограничение organic-v1: candidate pool пока начинается с bounded canonical catalog, отсортированного по новизне. Очень старый Space вне первых 200 кандидатов может не попасть в персонализированный ranking даже при новой активности. До beta candidate generation будет собираться из нескольких bounded источников (recent activity/upcoming/shared context), а не через unbounded scan.

## Stage 5.6 — Web application maturity 🚧 `0.5.5-alpha.0`

Следующий продуктово-технический slice:

- PWA manifest/installability и offline shell;
- service-worker strategy без кеширования security-sensitive API/auth responses;
- notification worker adapter foundation и reusable delivery contracts;
- frontend state/testing cleanup;
- route/error/loading/offline consistency;
- дальнейшее удаление legacy styles/components;
- accessibility pass для новых Stage 5 surfaces;
- подготовка SPA contracts к future Android/iOS clients без browser-only business logic.

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
- notification reconciliation load/idempotency tests;
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
- status/incident process;
- deployment/recovery documentation;
- shared/object storage.

### UX/accessibility
- keyboard/focus audit;
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
- Communication quality first.
- Никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
- UI/UX развивается вместе с доменной моделью.
