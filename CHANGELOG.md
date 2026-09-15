# PubChat — история версий

Формат версий: `MAJOR.MINOR.PATCH-channel.N` до стабильного `1.0.0`.

## [Unreleased] — 0.4.0-alpha.0

Stage 4: Living Spaces & Social Core. Функциональный scope реализован, но версия ещё не назначена релизным checkpoint: требуется exact-head quality gate и отдельный version bump.

### Living Spaces
- канонический `/spaces/v1` domain поверх legacy `rooms/messages` без destructive rewrite;
- additive settings, memberships, tags и backfill существующих комнат;
- public / unlisted / private visibility, private = invite-only;
- open / request / invite membership flows;
- canonical membership lifecycle и scoped owner/moderator/member roles;
- pagination, заявки на вступление, approve/reject/remove;
- realtime access зависит от canonical active membership;
- Space Discovery, route-driven conversation и новый create flow;
- Unicode-safe legacy tag backfill.

### Social graph / privacy
- `/social/v1` follow/unfollow;
- friend request / accept / reject / remove;
- account-level block/unblock;
- privacy-aware people discovery;
- direct profile access подчиняется тем же privacy/block правилам;
- location показывается только по privacy consent;
- account-bound Space invitations с TTL и повторной проверкой block/ban/capacity;
- SPA-разделы «Люди» и «Приглашения».

### Living community
- Space Rules;
- scheduled Events с UTC-normalization;
- append-only Space History;
- Центр пространства `/spaces/:uid/community`;
- правила/события сохраняются при удалении аккаунта автора;
- manager-only вход из Центра в moderation queue.

### Transparent moderation
- `/moderation/v1` reports / actions / appeals;
- private reports для команды пространства;
- scoped warning и restrict без тюремной терминологии;
- restrict синхронизирован с точным legacy `RoomBan` и cross-worker disconnect;
- Safety Center пользователя;
- manager moderation queue;
- one appeal per action на уровне БД;
- one moderation action per report на уровне БД;
- original decision maker не может рассматривать собственную апелляцию;
- overturn отзывает именно связанное ограничение;
- повторный restrict отзывает предыдущее активное ограничение и закрывает его незавершённую апелляцию;
- закрытые/уже обработанные жалобы нельзя повторно использовать для нового action;
- private report metadata проверяется только после scoped manager authorization.

### SPA / UI/UX
- Space Discovery вместо legacy списка комнат;
- People/relationship flows;
- canonical member/presence separation;
- mobile-first навигация;
- rules/events/history surfaces;
- Safety Center и manager moderation UI;
- terminology приведена к концепции PubChat: Space, участие, ограничение доступа, апелляция.

### Release gate
Перед фиксацией `0.4.0-alpha.1` обязательны:
- backend compile/import/contracts;
- ровно одна Alembic head;
- frontend production build;
- final privacy/permission self-review;
- canonical `VERSION` bump;
- повторный exact-head CI уже на финальном номере версии.

## [0.3.0-alpha.1] — 2026-09-15

Первая формально зафиксированная версия проекта после ревизии Stage 1–3.

### Realtime v2
- одноразовые scoped WebSocket tickets вместо JWT в URL;
- Redis pub/sub, distributed presence, heartbeat и cross-worker delivery;
- reconnect/resume, rate limiting и server-side idempotency;
- bounded socket send latency и cleanup stale connections.

### Privacy / security
- browser access token хранится только в памяти SPA;
- HttpOnly refresh session сохранена как долговременная сессия;
- серверное применение DM policy и block rules;
- CI guards против credentials в WebSocket URL и persistent access-token storage.

### Client
- connection state machine и автоматический reconnect;
- offline/reconnect UX без full-page failure;
- mobile-first application shell и обновлённый Space/DM transport.

### Quality gate
- backend compile/import;
- единственная Alembic head;
- Identity + Realtime contract tests;
- frontend production build;
- security regression guards.

## [0.2.0-alpha.1] — 2026-09-15

Stage 2: Identity v2 и SPA application shell.

- `Account != Persona`;
- Credential, IdentitySession, PrivacySettings, relationships и platform RBAC;
- additive migration/backfill legacy users;
- hashed refresh-token sessions;
- `/identity/v2` register/login/refresh/logout/me/profile/privacy API;
- Persona-first registration и privacy-aware profiles;
- app shell, light/dark design tokens и mobile navigation;
- Identity contract tests и production frontend build.

## [0.1.0-alpha.1] — 2026-09-15

Stage 1: revival foundation и security baseline.

- product/revival architecture зафиксирована;
- backend admin RBAC закрыт server-side;
- profile IDOR и mass-assignment устранены;
- sensitive user projections закрыты от анонимного доступа;
- JWT secrets и token logging исправлены;
- database health-check исправлен;
- добавлен GitHub Actions CI.

## [0.0.0-alpha.0] — legacy baseline

Исходное состояние старого проекта до revival. Это историческая точка отсчёта, а не рекомендуемый к запуску релиз.
