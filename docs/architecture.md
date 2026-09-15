# Архитектура PubChat

## 1. Архитектурная модель

PubChat — modular monolith с отдельным Vue SPA-клиентом.

- Backend отвечает за identity, privacy, permissions, social graph, messaging rules, moderation, discovery, persistence и realtime contracts.
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

Block всегда проверяется на Account-level и должен влиять на новые social features, включая support/gifts и discovery.

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

`SpaceActivity` — canonical recurring template. Начиная с `0.5.2-alpha.1`, конкретные встречи материализуются отдельно как bounded `ActivityOccurrence`, но template остаётся источником истины.

### Conversation Rounds

Activity-scoped social prompts:

- icebreaker;
- choice;
- story_chain.

Один open round на Activity и один response на Account+round закреплены DB constraints.

### Achievements

`AchievementDefinition` + `AccountAchievement`.

Grant выполняют только backend system hooks. Public projection не раскрывает private source/context.

## 9. Occurrences & Notifications

Выпущено в `0.5.2-alpha.1`.

- `ActivityOccurrence` — bounded concrete occurrence;
- `ActivityReminderPreference` — private Account opt-in;
- `UserNotification` — private inbox.

Recurring template остаётся источником истины. Occurrences материализуются только в ограниченном горизонте и имеют уникальность `(activity_uid, starts_at)`.

Reconciliation idempotent и пригоден для двух вызывающих слоёв:

- SPA sync сейчас;
- background worker/native push adapter позже.

## 10. Creator Support & Cosmetic Gifts

Выпущено в `0.5.3-alpha.1`.

Сущности:

- `CreatorSupportProfile` — opt-in Persona support policy;
- `SpaceSupportSettings` — scoped Space support policy;
- `GiftDefinition` — allowlisted gift catalog;
- `SupportLedgerEntry` — append-only historical support record;
- `CosmeticEntitlement` — живой cosmetic artifact Persona/Space.

Архитектурные границы:

- support settings выключены по умолчанию;
- Persona support повторно использует profile privacy + Account block;
- Space send требует active membership, manager settings/history — scoped owner/moderator;
- public shelf — только aggregate gift/count;
- sender/message остаются private history;
- ledger snapshot не используется как live authorization source;
- Account row lock сериализует sender anti-spam count;
- gift/entitlement не меняет trust, permissions, moderation authority или discovery ranking;
- `0.5.3` не содержит wallet/currency/checkout/payment-provider state.

Реальный money flow, если будет добавлен позже, должен стать отдельным financial domain с provider-event idempotency, fraud/refund/chargeback lifecycle и жёсткой границей между financial state и social authority.

## 11. Explainable Organic Discovery

Выпущено в `0.5.4-alpha.1`.

`/spaces/v1` остаётся стабильным каталогом/management contract. Персонализированная выдача вынесена в `/discovery/v1/spaces`.

Pipeline:

```text
canonical eligibility -> block/privacy suppression -> bounded candidate context -> organic score -> diversity -> explainable projection
```

Сигналы organic-v1:

- distinct recent authors;
- nearest allowed Activity/Event;
- shared tags/purpose;
- explicit Persona social intent;
- modest freshness/member-count context;
- weak membership/pending context.

Score остаётся server-only. Клиент получает только до трёх reasons и optional upcoming context.

Не используются legacy `Room.rating`, support/gifts, price/currency/payment или moderation authority.

Privacy rule важнее ranking: алгоритм не может сделать недопустимый Space видимым и не раскрывает upcoming details private/unlisted Space без active membership.

Текущий bounded pool ограничен 200 canonical candidates и пока bias-ится к новым Spaces из-за исходной catalog ordering. До beta candidate generation должен комбинировать несколько bounded источников активности/контекста без unbounded scan.

## 12. Data boundaries

### PostgreSQL

Хранит durable domain state. Любое важное business decision должно быть восстанавливаемо из PostgreSQL.

### Redis

Не является permanent database продукта. Если Redis очищен, permanent relationships/messages/moderation/history не должны исчезать.

### Local files

`backend/uploads` — текущая compatibility/local development storage. Для multi-instance production требуется shared/object storage.

## 13. API boundaries

Новые домены используют versioned prefixes, например:

- `/identity/v2`;
- `/realtime/v2`;
- `/spaces/v1`;
- `/social/v1`;
- `/moderation/v1`;
- `/appearance/v1`;
- `/activities/v1`;
- `/achievements/v1`;
- `/activity-occurrences/v1`;
- `/notifications/v1`;
- `/support/v1`;
- `/discovery/v1`.

ORM object не является API DTO. Public/private projections должны быть явными.

## 14. UI architecture

SPA route-driven. Основные области:

- Space Discovery;
- People;
- Messenger;
- Profile/Persona;
- Space conversation;
- Space Community;
- Space Life;
- Space Support;
- Safety/Moderation;
- Achievements;
- Notifications.

Backend remains authoritative для permissions. Frontend route guards — только UX hint.

## 15. Legacy debt

До beta ещё остаются compatibility зависимости от:

- `users`;
- `rooms`;
- `room_members`;
- `room_bans`;
- части legacy messenger/chat models.

Удаление делается постепенно. Требование — data-preserving migrations и отсутствие big-bang rewrite.

## 16. Non-negotiable architecture invariants

- Account != Persona.
- Reputation != Permission.
- Space role != Platform role.
- Block — Account-level.
- Backend owns authorization.
- PostgreSQL owns durable truth.
- Redis owns only ephemeral/distributed realtime state.
- WebSocket credentials never appear in URL.
- Browser access JWT is memory-only.
- Monetary/cosmetic systems cannot modify trust/moderation authority/discovery ranking.
- Discovery ranking cannot expand eligibility/privacy.
