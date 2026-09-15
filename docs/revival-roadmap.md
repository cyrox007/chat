# PubChat Revival Roadmap

## Delivery rule

Разработка идёт короткими этапами в отдельных ветках. Каждый завершённый этап проходит сравнение/проверки, оформляется pull request и после успешной проверки сливается в `main`.

UI/UX развивается **параллельно** с архитектурой и backend. Каждый этап, который вводит или меняет пользовательскую сущность, обязан одновременно обновлять соответствующие экраны, термины, состояния и компоненты UI Kit. Мы не откладываем дизайн «на потом» и не делаем big-bang redesign в конце проекта.

Базовые правила UI/UX зафиксированы в `docs/ui-ux-kit.md`.

## Stage 1 — Foundation & security baseline ✅ merged

Цель: сделать старое ядро безопасной отправной точкой, не меняя продукт целиком.

- зафиксирована новая концепция PubChat;
- закрыт критический доступ к `/admin/*` без admin-role;
- закрыты IDOR и mass assignment в обновлении профиля;
- access/refresh token material удалён из логов;
- убраны production-capable default JWT secrets;
- исправлен базовый DB health-check lifecycle;
- добавлен CI для backend/frontend quality gate.

## Stage 2 — Identity v2 ✅ merged

Цель: перестать использовать монолитную таблицу `users` как identity + profile + security + reputation одновременно.

Реализовано:

- `Account`;
- `Persona` / public profile projection;
- `Credential`;
- `IdentitySession`;
- `Role` / `Permission` foundation;
- `PrivacySettings`;
- `AccountRelationship`;
- отдельные public/private projections;
- Persona-first onboarding;
- SPA application shell и mobile navigation.

## Stage 3 — Realtime v2 ✅ merged

Цель: сделать realtime устойчивым и масштабируемым.

Реализовано:

- WebSocket auth без JWT в URL;
- one-time scoped socket tickets и auth handshake;
- Redis pub/sub и distributed delivery;
- distributed presence;
- heartbeat;
- reconnect/resume с client state machine;
- server-side idempotency по client event id (`frontId`);
- rate limiting;
- multi-worker support;
- browser access JWT только в памяти SPA;
- privacy-aware DM policy на сервере;
- исправление ownership read receipts;
- cross-worker Space restrictions;
- CI security regression guards;
- reconnect/offline UX и mobile-first realtime surfaces.

Stage 3 включён в релизную базу `0.3.0-alpha.1`.

## Stage 4 — Living Spaces & social core 🚧 release gate

Цель: реализовать продуктовую основу PubChat и заменить legacy `Room` продуктовой моделью Living Spaces без destructive rewrite.

### Реализовано

- versioned `/spaces/v1` contract поверх legacy `rooms/messages`;
- additive `space_settings`, `space_memberships`, `space_tags` и backfill;
- public / unlisted / private visibility;
- private Space = invite-only;
- open / request / invite membership policy;
- canonical membership lifecycle и пагинация;
- scoped owner / moderator / member roles;
- realtime access зависит от canonical active membership;
- Space Discovery и route-driven conversation `/spaces/:uid`;
- новый create Space flow и canonical People panel;
- `/social/v1`: follow, friendship requests, friendship, block/unblock;
- privacy-aware people discovery и direct profile access;
- account-bound Space invitations с TTL;
- экраны «Люди» и «Приглашения»;
- Space Rules;
- scheduled Events;
- append-only Space History;
- Центр пространства `/spaces/:uid/community`;
- transparent moderation `/moderation/v1`;
- private reports;
- scoped warning/restrict actions;
- exact bridge к legacy `RoomBan` для enforcement;
- Safety Center пользователя;
- manager moderation queue;
- one appeal per action;
- independent appeal reviewer;
- overturn снимает именно связанное ограничение;
- повторный restrict помечает предыдущее действие как `superseded`;
- UI/UX обновляется одновременно с доменом, включая mobile states.

### Gate для `0.4.0-alpha.1`

- exact-head backend compile/import/tests;
- ровно одна Alembic migration head;
- production SPA build;
- final privacy/permission self-review;
- обновление `CHANGELOG.md`;
- bump canonical `VERSION`;
- повторный exact-head CI уже на версии `0.4.0-alpha.1`;
- только затем PR переводится из draft и сливается в `main`.

### Осознанный технический долг после alpha checkpoint

- устранить race вокруг member capacity при конкурентных join/approve;
- продолжить уменьшение зависимости от legacy `users/rooms/room_members/room_bans`;
- расширить integration tests реальной PostgreSQL/Redis средой;
- observability, metrics и нагрузочные сценарии до beta.

## Stage 5 — Product identity & engagement

Цель: дать PubChat собственный характер поверх уже устойчивого social core.

Планируемый scope:

- Persona customization;
- оформление Living Spaces;
- achievements без pay-to-status;
- совместные события и recurring activities;
- social-first mini-games, которые создают повод разговаривать;
- creator support;
- косметическая экономика без pay-to-win;
- более качественный discovery/ranking Spaces без покупки социального влияния;
- PWA/mobile shell после стабилизации web/realtime.

Параллельный UI/UX scope:

- визуальная индивидуальность Persona;
- customization Spaces;
- social-first game surfaces;
- creator support flows;
- polished onboarding;
- унификация и постепенное удаление legacy styles/components.

## Pre-beta hardening

До первой beta обязательно:

- production-like PostgreSQL + Redis integration tests;
- migrations upgrade/downgrade rehearsal на копии legacy schema;
- load tests realtime и Space discovery;
- observability/status/incident surfaces;
- accessibility pass;
- security review session/token/media/upload/moderation paths;
- отсутствие известных P0/P1 launch blockers.

## Non-negotiable invariants

- Account != Persona.
- Reputation != permissions.
- Space moderator != platform moderator.
- Деньги не покупают trust и moderation power.
- Блокировка Account не обходится новой Persona.
- Communication quality first.
- Никакой тюремной терминологии.
- UI/UX развивается одновременно с доменной моделью.
- Mobile является полноценным основным сценарием, а не уменьшенной desktop-версией.
- SPA является первым клиентом, но backend/API/realtime contracts проектируются reusable для будущих Android/iOS клиентов.
