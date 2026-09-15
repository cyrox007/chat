# Дорожная карта PubChat

## Текущий статус

Released: **`0.5.1-alpha.1`**.

In development: **`0.5.2-alpha.0`** — Activity Occurrences & Notifications.

PubChat остаётся alpha: продуктовые контуры уже сформированы, но production-like hardening и часть engagement/creator/discovery задач ещё не завершены.

## Завершённые этапы

### Stage 1 — Foundation & Security ✅ `0.1.0-alpha.1`

- зафиксирована новая концепция PubChat;
- закрыты критические authorization/data exposure проблемы legacy backend;
- исправлены secrets/logging/DB health issues;
- введён CI.

### Stage 2 — Identity v2 ✅ `0.2.0-alpha.1`

- Account/Persona/Credential/IdentitySession;
- PrivacySettings и AccountRelationship;
- platform RBAC foundation;
- Persona-first onboarding;
- новый SPA shell и design tokens.

### Stage 3 — Realtime v2 ✅ `0.3.0-alpha.1`

- one-time ticket handshake без credential в WebSocket URL;
- Redis pub/sub/presence/rate limits/idempotency;
- multi-worker delivery;
- heartbeat/reconnect/resume;
- memory-only browser access JWT;
- privacy-aware DM policy.

### Stage 4 — Living Spaces & Social Core ✅ `0.4.0-alpha.1`

- `/spaces/v1`, canonical memberships и scoped roles;
- Space Discovery/create/join/request/invite;
- People/social graph/friend/follow/block;
- privacy-aware discovery;
- Rules, Events, History;
- Safety Center;
- reports/actions/appeals и manager moderation queue;
- terminology без тюремной метафоры.

### Stage 5.1 — Product Identity & Activities ✅ `0.5.0-alpha.1`

- Persona Appearance;
- Space Appearance;
- recurring Activities;
- RSVP;
- `next_starts_at`;
- mobile-first customization/activity UI.

### Stage 5.2 — Social Engagement ✅ `0.5.1-alpha.1`

- earned achievements;
- public shelf + private own history;
- Conversation Rounds: icebreaker/choice/story_chain;
- anti-competitive invariants: нет score/winner/prize/stake;
- block/membership/scoped-role integration.

## Stage 5.3 — Activity Occurrences & Notifications 🚧 `0.5.2-alpha.0`

Цель: превратить recurring Activity из абстрактного шаблона в понятные ближайшие встречи и opt-in напоминания.

### Уже реализовано в ветке

- bounded `ActivityOccurrence` rows;
- 45-day materialization horizon;
- unique Activity+start invariant;
- recurrence utility и regression для monthly anchor;
- private reminder preferences;
- lead time 15m / 60m / 1d;
- private notification inbox;
- one reminder max per occurrence;
- explicit idempotent reconciliation/sync;
- `/activity-occurrences/v1` и `/notifications/v1`;
- Notification SPA service;
- `/notifications` screen;
- обновление основной документации проекта.

### Осталось до `0.5.2-alpha.1`

- batch reminder state integration в Space Life;
- app-shell unread indicator + sync lifecycle;
- ownership/timezone/spam/privacy self-review;
- UI Kit/release checklist sync;
- exact-head CI;
- bump `VERSION`;
- второй exact-head CI;
- squash merge в `main`.

Browser/native push не входит в этот checkpoint: сначала стабилизируется in-app notification domain.

## Stage 5.4 — Creator support & cosmetic economy

Планируется после notification slice.

Цели:

- creator support без покупки власти;
- косметические каталоги/подарки;
- прозрачные ownership/entitlement records;
- никаких paid trust/moderation/discovery guarantees;
- fraud/chargeback boundaries до реальных платежей;
- UI, где support не превращает общение в витрину донатов.

Реальные payments не должны включаться до отдельного financial/security review.

## Stage 5.5 — Discovery quality

- activity-aware Space discovery;
- рекомендации по intent/interests/shared context;
- freshness/activity signals;
- diversity controls;
- block/privacy invariants;
- отсутствие платной покупки органического trust/ranking;
- объяснимые причины рекомендаций там, где это полезно.

## Stage 5.6 — Web application maturity

- PWA shell/offline-safe static experience;
- installability;
- notification worker adapter после стабилизации domain inbox;
- подготовка contracts для native push;
- frontend state/testing cleanup;
- дальнейшее удаление legacy styles/components.

## Stage 6 — Pre-beta hardening

Это обязательный gate перед `beta`, а не необязательная полировка.

### Data/migrations

- PostgreSQL integration test environment;
- Redis integration tests;
- full migration rehearsal с legacy schema/data copy;
- backup/restore drill;
- member-capacity concurrency hardening.

### Reliability/performance

- realtime load tests;
- Space discovery load tests;
- DB query profiling;
- Redis failure/recovery scenarios;
- slow client/backpressure scenarios;
- notification reconciliation load/idempotency tests.

### Security/privacy

- session/cookie/CSRF review;
- upload/media review;
- moderation/report/appeal review;
- privacy side-channel review;
- Account-level block coverage для всех новых social surfaces.

### Operations

- structured logs;
- metrics;
- error tracking;
- status/incident process;
- deployment/recovery documentation;
- shared/object storage решение.

### UX/accessibility

- keyboard/focus audit;
- contrast/accessibility pass;
- narrow/mobile viewport pass;
- error/empty/offline consistency;
- onboarding usability;
- terminology audit.

## Beta

Первая beta назначается только когда:

- все launch-critical user journeys работают end-to-end;
- нет известных P0/P1 launch blockers;
- production-like PostgreSQL/Redis gate пройден;
- migration/backup/recovery rehearsed;
- observability работает;
- responsive/accessibility baseline подтверждён;
- architecture-level rewrites прекращаются и фокус смещается на stabilization.

Ориентир версии: `0.9.0-beta.1`, но номер не назначается заранее ради календаря.

## Stable 1.0

`1.0.0` — первый public stable release с явным compatibility commitment API/data contracts.

## Постоянные инварианты

- Account != Persona.
- Reputation/achievement != Permission.
- Space moderator != Platform moderator.
- Деньги не покупают trust/moderation authority.
- Account block нельзя обойти другой Persona.
- Communication quality first.
- Никакой тюремной терминологии.
- SPA — первый клиент, API/realtime reusable для Android/iOS.
- UI/UX развивается вместе с доменной моделью, а не после backend.
