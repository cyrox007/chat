# PubChat — история версий

Формат версий: `MAJOR.MINOR.PATCH-channel.N` до стабильного `1.0.0`.

## [Unreleased] — 0.4.0-alpha.0

Stage 4: Living Spaces & social graph. В разработке, не является релизом.

Планируемый состав:
- канонический Space domain поверх legacy rooms/messages;
- membership и scoped roles;
- discovery, join/request/invite flows;
- social graph и privacy-aware discovery;
- правила, события и история пространства;
- transparent moderation/report/appeal foundation.

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
