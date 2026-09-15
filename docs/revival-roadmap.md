# PubChat Revival Roadmap

## Delivery rule

Разработка идёт короткими этапами в отдельных ветках. Каждый завершённый этап проходит сравнение/проверки, оформляется pull request и после успешной проверки сливается в `main`.

UI/UX развивается **параллельно** с архитектурой и backend. Каждый этап, который вводит или меняет пользовательскую сущность, обязан одновременно обновлять соответствующие экраны, термины, состояния и компоненты UI Kit. Мы не откладываем дизайн «на потом» и не делаем big-bang redesign в конце проекта.

Базовые правила UI/UX зафиксированы в `docs/ui-ux-kit.md`.

## Stage 1 — Foundation & security baseline ✅ merged

Цель: сделать старое ядро безопасной отправной точкой, не меняя продукт целиком.

- зафиксировать новую концепцию PubChat;
- закрыть критический доступ к `/admin/*` без admin-role;
- закрыть IDOR и mass assignment в обновлении профиля;
- перестать писать access/refresh token material в логи;
- убрать production-capable default JWT secrets;
- исправить базовый DB health-check lifecycle;
- добавить минимальный CI для Python syntax и frontend build.

## Stage 2 — Identity v2 ✅ merged

Цель: перестать использовать монолитную таблицу `users` как identity + profile + security + reputation одновременно.

Целевые сущности:

- `Account`;
- `Persona` / `Profile`;
- `Credential`;
- `Session`;
- `Role` / `Permission`;
- `PrivacySettings`;
- `Relationship`;
- отдельные public/private projections.

В этом этапе переносим удачные инфраструктурные идеи из `BaseProjectPython`, но не копируем его корпоративную модель пользователя.

Параллельный UI/UX scope:

- design tokens и базовые primitives;
- auth/registration flow;
- Persona identity surfaces;
- Persona switcher foundation;
- social intent и privacy states;
- public/private profile projections в интерфейсе;
- системные feedback/error/loading patterns.

## Stage 3 — Realtime v2 🚧 merge gate

Цель: сделать realtime устойчивым и масштабируемым.

Реализовано в `revival/realtime-v2`:

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
- CI security regression guards.

Параллельный UI/UX scope:

- reconnect/offline states без пугающих full-screen ошибок;
- connection state в Spaces и DM;
- composer блокируется, когда transport не принимает действия;
- сохранение контекста при reconnect;
- mobile-first Space и messenger surfaces;
- терминология «пространство / ограничить доступ» вместо legacy punitive language.

До merge этап проходит полный diff-review, backend contracts, security guards и production frontend build.

## Stage 4 — Spaces & social graph ⏭ next

Цель: реализовать продуктовую основу PubChat и заменить legacy `Room` продуктовой моделью Living Spaces без destructive rewrite.

Первый scope:

- `Space` domain contract поверх/вместо legacy Room projection;
- membership и scoped roles;
- friends/follow/block как account relationships;
- social intent в discovery и коммуникации;
- privacy-aware discovery;
- правила пространства и membership policy;
- transparent moderation actions;
- reports/appeals foundation;
- reputation отдельно от permissions;
- события как часть Living Space history.

Параллельный UI/UX scope:

- Space discovery вместо простого списка комнат;
- Space header/presence/activity/history;
- member and scoped-role surfaces;
- community rules;
- события;
- consent-first DM entry points;
- transparent moderation and appeal flows;
- empty/loading/offline/mobile states как обязательная часть каждого flow.

## Stage 5 — Product identity

Цель: дать PubChat собственный характер.

- Persona customization;
- оформление пространств;
- achievements;
- совместные события;
- social-first mini-games;
- creator support;
- косметическая экономика без pay-to-win;
- PWA/mobile shell после стабилизации web/realtime.

Параллельный UI/UX scope:

- визуальная индивидуальность Persona без pay-to-status;
- customization Spaces;
- social-first game surfaces;
- creator support flows;
- polished onboarding;
- финальная унификация и удаление legacy styles/components.

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
