# PubChat Revival Roadmap

## Delivery rule

Разработка идёт короткими этапами в отдельных ветках. Каждый завершённый этап проходит сравнение/проверки, оформляется pull request и после успешной проверки сливается в `main`.

## Stage 1 — Foundation & security baseline

Цель: сделать старое ядро безопасной отправной точкой, не меняя продукт целиком.

- зафиксировать новую концепцию PubChat;
- закрыть критический доступ к `/admin/*` без admin-role;
- закрыть IDOR и mass assignment в обновлении профиля;
- перестать писать access/refresh token material в логи;
- убрать production-capable default JWT secrets;
- исправить базовый DB health-check lifecycle;
- добавить минимальный CI для Python syntax и frontend build.

## Stage 2 — Identity v2

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

## Stage 3 — Realtime v2

Цель: сделать realtime устойчивым и масштабируемым.

- WebSocket auth без JWT в URL;
- short-lived socket ticket или auth handshake;
- Redis pub/sub;
- presence;
- heartbeat;
- reconnect/resume;
- idempotent message IDs;
- rate limiting;
- multi-worker support;
- backpressure и telemetry.

## Stage 4 — Spaces & social graph

Цель: реализовать продуктовую основу PubChat.

- Living Spaces;
- membership и scoped roles;
- friends/follow/block;
- social intent;
- privacy;
- discovery;
- events;
- transparent moderation;
- reports/appeals;
- reputation отдельно от permissions.

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

## Non-negotiable invariants

- Account != Persona.
- Reputation != permissions.
- Space moderator != platform moderator.
- Деньги не покупают trust и moderation power.
- Блокировка Account не обходится новой Persona.
- Communication quality first.
- Никакой тюремной терминологии.
