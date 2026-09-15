# Дорожная карта PubChat

## Текущий статус

Released: **`0.5.2-alpha.1`**.

Next development line: **`0.5.3-alpha.0`** — Creator support & cosmetic economy foundation.

PubChat остаётся alpha: основные продуктовые контуры сформированы, но production-like hardening, creator/discovery maturity и pre-beta эксплуатационные проверки ещё не завершены.

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

## Stage 5.4 — Creator support & cosmetic economy 🚧 `0.5.3-alpha.0`

Цель: дать создателям и участникам способы поддерживать пространства и выражать отношение косметически, не превращая деньги в власть.

Первый slice:

- `CreatorProfile` / support eligibility без влияния на trust;
- каталог косметических gifts и entitlements;
- immutable ownership/support ledger;
- получение и отображение gifts в Persona/Space context;
- privacy-aware sender/recipient projections;
- manager не получает moderation/discovery boost за поддержку;
- no paid role / no paid trust / no paid ban immunity;
- сначала mock/internal support records, реальные payments только после отдельного financial/security review;
- UI/UX без агрессивных донатных механик и dark patterns.

Release gate: additive migrations, server-side entitlement rules, abuse/privacy review, SPA build, exact-head CI → version bump → второй CI.

## Stage 5.5 — Discovery quality

- activity-aware Space discovery;
- intent/interests/shared-context recommendations;
- freshness/activity signals и diversity controls;
- block/privacy invariants;
- отсутствие покупки органического trust/ranking;
- объяснимые recommendation reasons там, где они полезны.

## Stage 5.6 — Web application maturity

- PWA shell/installability;
- notification worker adapter и подготовка native push contracts;
- frontend state/testing cleanup;
- дальнейшее удаление legacy styles/components.

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
- notification reconciliation load/idempotency tests.

### Security/privacy
- session/cookie/CSRF review;
- upload/media review;
- moderation/report/appeal review;
- privacy side-channel review;
- Account block coverage для всех social surfaces.

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
- Communication quality first.
- Никакой тюремной терминологии.
- SPA — первый клиент, contracts reusable для Android/iOS.
- UI/UX развивается вместе с доменной моделью.
