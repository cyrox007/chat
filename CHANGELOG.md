# PubChat — история версий

Формат версий: `MAJOR.MINOR.PATCH-channel.N` до стабильного `1.0.0`.

## [Unreleased] — 0.5.0-alpha.0

Stage 5: Product Identity & Engagement. Первый slice построен поверх выпущенного `0.4.0-alpha.1` и проходит финальный release gate.

### Persona Appearance
- allowlisted accent/background/avatar-frame presets;
- короткая status line;
- appearance отделён от Account/security/trust/permissions;
- public appearance подчиняется существующим profile privacy/block rules;
- профиль деградирует к базовому виду, если cosmetic projection временно недоступен.

### Space Appearance
- theme/cover presets, ambient icon и welcome line;
- изменение оформления доступно только scoped owner/moderator;
- оформление не меняет visibility, membership policy, permissions или discovery power;
- privacy-aware batch projection до 100 Space UID без HTTP N+1;
- недоступные private Spaces не раскрываются через appearance batch;
- Space Discovery показывает атмосферу, но не использует cosmetics в сортировке.

### Recurring Activities
- versioned `/activities/v1` contract;
- activity types и recurrence rules из allowlist;
- `starts_at` требует explicit timezone;
- API возвращает UTC timestamps с `Z`;
- recurrence хранится одной canonical записью-шаблоном без бесконечной материализации строк;
- `next_starts_at` вычисляется при чтении для daily/weekly/monthly;
- RSVP `interested` / `going`;
- active membership требуется для RSVP;
- creator или scoped manager может редактировать/отменять activity;
- bulk RSVP projection без N+1 на списке.

### SPA / UI/UX
- экран «Стиль образа»;
- privacy-aware Persona appearance в обычном профиле;
- экран «Жизнь пространства»;
- appearance в Space Discovery;
- ближайшее occurrence recurring activity;
- RSVP и отмена activity;
- routes/context navigation и mobile-first customization/activity surfaces.

### Инварианты первого slice
- cosmetics != trust/reputation/permissions;
- Space appearance != discovery ranking power;
- нет внутренней валюты, loot boxes, marketplace или pay-to-status;
- recurring rule хранится как шаблон и не материализует бесконечную цепочку строк в БД.

### Release gate
Перед фиксацией `0.5.0-alpha.1` обязательны:
- branch синхронизирован с `main@0.4.0-alpha.1`;
- additive migration graph с одной Alembic head;
- backend compile/import/contracts;
- frontend production build;
- privacy/scoped-role/migration self-review;
- public appearance/UI Kit polish;
- canonical `VERSION` bump только после зелёного functional exact-head CI;
- повторный exact-head CI уже на `0.5.0-alpha.1` перед merge.

## [0.4.0-alpha.1] — 2026-09-15

Stage 4: Living Spaces & Social Core. Первый alpha-checkpoint продуктового социального ядра PubChat.

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
- terminology приведена к концепции PubChat: Space, участие, ограничение доступа, апелляция;
- legacy UTC timestamps нормализуются на SPA Space boundary.

### Quality gate
Перед version bump успешно прошли:
- backend dependency install, compile и FastAPI import;
- realtime security regression guard;
- ровно одна Alembic migration head;
- все backend contract tests;
- SPA security regression guard;
- production Vite build;
- final privacy/permission/migration self-review.

После version bump выполнен повторный exact-head CI; PR #4 слит только после его успешного завершения.

### Известный технический долг
- race вокруг member capacity при конкурентных join/approve будет отдельно harden перед beta;
- нужен platform-level fallback для апелляций, если в Space нет второго независимого manager;
- legacy `users/rooms/room_members/room_bans` остаются compatibility backbone для части домена;
- до beta нужны реальные PostgreSQL + Redis integration tests, migration rehearsal, observability и load testing.

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
