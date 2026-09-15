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

## Stage 4 — Living Spaces & social core ✅ merged

Цель: реализовать продуктовую основу PubChat и заменить legacy `Room` продуктовой моделью Living Spaces без destructive rewrite.

Реализовано:

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
- one appeal per action и one action per report — DB invariants;
- independent appeal reviewer;
- overturn снимает именно связанное ограничение;
- повторный restrict отзывает предыдущее активное решение и закрывает его pending appeal;
- закрыт side-channel приватных report metadata: consistency checks идут после scoped manager authorization;
- legacy tag backfill не зависит от locale PostgreSQL и безопасен для Unicode;
- UI/UX обновляется одновременно с доменом, включая mobile states.

Stage 4 выпущен как `0.4.0-alpha.1` после двухступенчатого exact-head CI.

### Осознанный технический долг после Stage 4

- устранить race вокруг member capacity при конкурентных join/approve;
- добавить platform-level fallback для апелляций, если в Space нет второго независимого manager;
- продолжить уменьшение зависимости от legacy `users/rooms/room_members/room_bans`;
- расширить integration tests реальной PostgreSQL/Redis средой;
- observability, metrics и нагрузочные сценарии до beta.

## Stage 5 — Product identity & engagement 🚧 active

Цель: дать PubChat собственный характер и причины возвращаться поверх устойчивого social core — без покупки социального влияния и без азартной экономики.

### Stage 5.1 — Persona / Space identity + recurring Activities ✅ merged

Выпущено как `0.5.0-alpha.1`:

- Persona Appearance: allowlisted accent/background/avatar-frame presets + status line;
- privacy-aware appearance в обычном Persona profile;
- Space Appearance: theme/cover/icon/welcome line;
- privacy-aware bounded batch projection без HTTP N+1;
- cosmetics не влияют на discovery ranking;
- recurring Activities `none/daily/weekly/monthly` как canonical templates;
- explicit timezone input и UTC `Z` output;
- вычисляемый `next_starts_at` без бесконечной материализации occurrence rows;
- RSVP `interested/going`;
- creator/scoped manager может отменять Activity;
- экран «Стиль образа», Space appearance в discovery и «Жизнь пространства».

### Stage 5.2 — Earned Achievements & Conversation Rounds 🚧 release gate

Development line: `0.5.1-alpha.0`.

Реализовано:

- system-only achievements catalog + account awards;
- read-only `/achievements/v1` API;
- achievement source/context доступен только владельцу Account;
- публичный achievement shelf подчиняется profile privacy/block;
- достижения `first_host`, `conversation_starter`, `first_round_response`;
- достижения не дают trust/permissions/reputation/discovery advantage;
- Activity-scoped Conversation Rounds: `icebreaker`, `choice`, `story_chain`;
- один open round на Activity — PostgreSQL invariant;
- один response на Account+round;
- active Space membership обязательно для участия;
- Activity creator или scoped owner/moderator управляет round;
- Account-level block скрывает round responses в обе стороны;
- отмена Activity завершает open round в той же транзакции;
- public Persona achievement shelf;
- собственная история достижений;
- Conversation Rounds встроены в «Жизнь пространства»;
- choice показывает распределение, но не определяет победителя;
- отсутствуют score/rank/prize/stake/currency/payment поля.

Gate перед `0.5.1-alpha.1`:

- additive migration graph с одной Alembic head;
- backend compile/import/security/contracts;
- SPA security guard + production build;
- abuse/privacy/permissions self-review;
- changelog/versioning/UI kit sync;
- canonical `VERSION` bump только после зелёного functional exact-head CI;
- повторный exact-head CI уже на `0.5.1-alpha.1`;
- затем PR переводится из draft и сливается в `main`.

### Следующие Stage 5 slices

После `0.5.1` рассматриваются отдельно и только после product review:

- дополнительные social activity templates без leaderboard/stakes;
- creator support без продажи прав/trust;
- косметическая экономика без pay-to-win/pay-to-status;
- улучшение discovery quality без покупки социального влияния;
- PWA/mobile shell после стабилизации web/realtime;
- polished onboarding и дальнейшее удаление legacy styles/components.

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
- Achievements != reputation/permissions.
- Social games создают разговор, а не победителей и ставки.
- Communication quality first.
- Никакой тюремной терминологии.
- UI/UX развивается одновременно с доменной моделью.
- Mobile является полноценным основным сценарием, а не уменьшенной desktop-версией.
- SPA является первым клиентом, но backend/API/realtime contracts проектируются reusable для будущих Android/iOS клиентов.
