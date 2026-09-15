# Архитектура PubChat

## 1. Архитектурная модель

PubChat — modular monolith с отдельным Vue SPA-клиентом.

- Backend отвечает за identity, privacy, permissions, social graph, messaging rules, moderation, persistence и realtime contracts.
- Frontend отвечает за navigation, presentation, responsive UX и client-side application state.
- PostgreSQL — authoritative persistent storage.
- Redis — ephemeral/distributed realtime storage и transport coordination.
- HTTP API и WebSocket contracts проектируются независимо от Vue, чтобы их могли использовать будущие Android/iOS клиенты.

Главное правило: бизнес-правила не должны существовать только во frontend.

## 2. Репозиторий

```text
.
├── backend/
│   ├── alembic/                 # migrations
│   ├── components/              # доменные модели/services/schemas
│   ├── views/                   # FastAPI HTTP/WS routers
│   ├── services/                # compatibility/application services
│   ├── socket_manager/          # websocket connection layer
│   ├── tests/                   # contract/regression tests
│   ├── app.py                   # FastAPI composition root
│   ├── database.py              # async SQLAlchemy engine/session
│   └── settings.py              # environment configuration
├── frontend/
│   ├── src/API/                 # HTTP/realtime client services
│   ├── src/components/          # reusable UI
│   ├── src/router/              # SPA routes
│   ├── src/stores/              # Vuex application state
│   ├── src/views/               # route-level screens
│   └── src/assets/              # design tokens/global styles
├── docs/
├── VERSION
└── CHANGELOG.md
```

## 3. Identity domain

Identity v2 разделяет ранее монолитный legacy `User`.

### Account

Скрытая platform identity:

- lifecycle/status;
- security identity;
- roles/permissions;
- relationships на Account-level;
- session ownership.

### Persona

Публичный социальный образ:

- handle/display name;
- avatar;
- bio;
- social intent;
- публичное appearance.

Правило: `Account != Persona`.

### Credential

Authentication credential/recovery/verification слой. Security material не должен находиться в публичном Persona projection.

### IdentitySession

Refresh session/device lifecycle. Refresh token хранится server-side в hashed representation; browser получает HttpOnly cookie. Access token короткоживущий и хранится SPA только в памяти.

### PrivacySettings

Отдельная сущность для DM/profile/location policy. Privacy применяется backend, а не только скрывает UI.

## 4. Living Spaces

Legacy таблица `rooms` пока остаётся compatibility backbone, но внешний продуктовый contract — `Space`.

Canonical дополнительные сущности:

- `SpaceSettings`;
- `SpaceMembership`;
- `SpaceTag`;
- `SpaceInvitation`;
- `SpaceRule`;
- `SpaceEvent`;
- `SpaceHistoryEntry`;
- `SpaceAppearance`;
- `SpaceActivity`.

### Membership

Membership имеет lifecycle, а не только факт строки в legacy join table. Scoped role принадлежит конкретному Space.

Ownership/permissions основываются на Account UID.

### Compatibility strategy

Мы не делаем destructive rename/rewrite старых `rooms/messages/room_members` одним релизом. Новые versioned API постепенно становятся canonical, а compatibility слой удаляется только после migration rehearsal и достаточного покрытия.

## 5. Social graph

`AccountRelationship` хранит Account-level связи.

Поддерживаются:

- follow;
- friend_request;
- friend;
- block.

Accepted friendship совместима с DM mutual policy через двустороннюю friendship semantic.

Block всегда проверяется на Account-level и должен влиять на новые social features.

## 6. Messaging и Realtime v2

HTTP authentication и WebSocket authentication разделены.

Сценарий WebSocket:

1. Authenticated HTTP request выдаёт короткоживущий one-time ticket.
2. SPA открывает WebSocket URL без credential.
3. Ticket отправляется первым WebSocket frame.
4. Backend consume-ит ticket один раз и подтверждает `realtime_ready`.

Redis используется для:

- ticket state;
- pub/sub;
- presence;
- cross-worker delivery/control;
- rate limiting;
- idempotency.

Локальные `WebSocket` objects остаются только внутри конкретного process/worker.

## 7. Moderation

Canonical workflow:

```text
Report -> Review -> ModerationAction -> optional Appeal -> Appeal review
```

Сущности:

- `ModerationReport`;
- `ModerationAction`;
- `ModerationAppeal`.

Space-level restriction временно bridge-ится в точный legacy `RoomBan`, чтобы enforcement и realtime disconnect продолжали работать во время миграции.

Reports приватны. Transparency означает понятное решение, причину, срок и право на апелляцию, а не публикацию конфликтов всему сообществу.

## 8. Product identity и engagement

### Appearance

`PersonaAppearance` и `SpaceAppearance` — cosmetic-only.

Они не могут изменять:

- roles;
- permissions;
- trust;
- moderation power;
- discovery ranking.

### Activities

`SpaceActivity` — canonical recurring template. В released `0.5.1-alpha.1` ближайшее время вычисляется как `next_starts_at` без материализации бесконечного ряда.

### Conversation Rounds

Activity-scoped social prompts:

- icebreaker;
- choice;
- story_chain.

Один open round на Activity и один response на Account+round закреплены DB constraints.

### Achievements

`AchievementDefinition` + `AccountAchievement`.

Grant выполняют только backend system hooks. Public projection не раскрывает private source/context.

## 9. Occurrences & Notifications — In development

Development-line `0.5.2-alpha.x` добавляет:

- `ActivityOccurrence` — bounded concrete occurrence;
- `ActivityReminderPreference` — private Account opt-in;
- `UserNotification` — private inbox.

Recurring template остаётся источником истины. Occurrences материализуются только в ограниченном горизонте и имеют уникальность `(activity_uid, starts_at)`.

Reconciliation idempotent и пригоден для двух вызывающих слоёв:

- SPA sync сейчас;
- background worker/native push adapter позже.

## 10. Data boundaries

### PostgreSQL

Хранит durable domain state. Любое важное business decision должно быть восстанавливаемо из PostgreSQL.

### Redis

Не является permanent database продукта. Если Redis очищен, permanent relationships/messages/moderation/history не должны исчезать.

### Local files

`backend/uploads` — текущая compatibility/local development storage. Для multi-instance production требуется shared/object storage.

## 11. API boundaries

Новые домены используют versioned prefixes, например:

- `/identity/v2`;
- `/realtime/v2`;
- `/spaces/v1`;
- `/social/v1`;
- `/moderation/v1`;
- `/appearance/v1`;
- `/activities/v1`;
- `/achievements/v1`;
- `/notifications/v1` — development.

ORM object не является API DTO. Public/private projections должны быть явными.

## 12. UI architecture

SPA route-driven. Основные области:

- Space Discovery;
- People;
- Messenger;
- Profile/Persona;
- Space conversation;
- Space Community;
- Space Life;
- Safety/Moderation;
- Achievements;
- Notifications — development.

Backend remains authoritative для permissions. Frontend route guards — только UX hint.

## 13. Legacy debt

До beta ещё остаются compatibility зависимости от:

- `users`;
- `rooms`;
- `room_members`;
- `room_bans`;
- части legacy messenger/chat models.

Удаление делается постепенно. Требование — data-preserving migrations и отсутствие big-bang rewrite.

## 14. Non-negotiable architecture invariants

- Account != Persona.
- Reputation != Permission.
- Space role != Platform role.
- Block — Account-level.
- Backend owns authorization.
- PostgreSQL owns durable truth.
- Redis owns only ephemeral/distributed realtime state.
- WebSocket credentials never appear in URL.
- Browser access JWT is memory-only.
- Monetary/cosmetic systems cannot modify trust/moderation authority.
