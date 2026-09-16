# PubChat

PubChat — SPA-приложение для свободного общения и живых тематических сообществ. Пользователь создаёт Persona, входит в Living Spaces, общается в realtime, участвует в событиях и активностях, строит социальные связи и управляет приватностью.

Проект не является копией Galaxy: PubChat развивает собственную концепцию без покупки социального влияния и без тюремной терминологии.

## Статус

Текущий выпущенный checkpoint: `0.6.6-alpha.1`.

Текущая development-линия: `0.6.x-alpha` — Pre-beta hardening продолжается.

Stage 6 уже закрепил PostgreSQL 16 migration/integration/recovery baseline, Redis 7.2 distributed realtime, restart/recovery и real Sentinel master-promotion baseline, real multi-process Uvicorn/WebSocket rehearsal с rolling restart и bounded per-socket backpressure. Production backend запускается за постоянным systemd-owned listener, routine deploy меняет workers rolling reload без намеренного `502` окна, а frontend публикуется staged/asset-first. Production outage не маскируется process-local fallback; direct Redis и Sentinel topology используют общий failover-aware realtime transport, а медленный WebSocket consumer изолируется собственной outbound queue и не блокирует fan-out другим клиентам.

До beta всё ещё нужны rehearsal на anonymized production-like snapshot, member-capacity concurrency/DST hardening, notification/message-delivery hardening, observability, security и финальные accessibility/browser/operations gates.

Канонический номер версии находится в `VERSION`, история выпусков — в `CHANGELOG.md`.

## Документация

Полный индекс: [`docs/README.md`](docs/README.md).

Основные документы:

- [`docs/installation.md`](docs/installation.md) — установка и первый запуск;
- [`docs/system-requirements.md`](docs/system-requirements.md) — системные требования;
- [`docs/user-guide.md`](docs/user-guide.md) — функции и пользовательские сценарии;
- [`docs/architecture.md`](docs/architecture.md) — архитектура;
- [`docs/api-and-realtime.md`](docs/api-and-realtime.md) — HTTP API и WebSocket;
- [`docs/security-and-privacy.md`](docs/security-and-privacy.md) — security/privacy model;
- [`docs/development.md`](docs/development.md) — разработка, миграции, тесты и CI;
- [`docs/operations.md`](docs/operations.md) — эксплуатация и reminder worker;
- [`docs/production-deploy-v1.md`](docs/production-deploy-v1.md) — persistent listener, staged SPA publish и health-gated rolling deploy;
- [`docs/message-notification-delivery-v1.md`](docs/message-notification-delivery-v1.md) — online/offline message routing, email nudge и Web Push plan;
- [`docs/browser-compatibility-v1.md`](docs/browser-compatibility-v1.md) — browser launch matrix и Safari registration audit;
- [`docs/prebeta-hardening-v1.md`](docs/prebeta-hardening-v1.md) — Stage 6 PostgreSQL/migration hardening baseline;
- [`docs/database-recovery-v1.md`](docs/database-recovery-v1.md) — PostgreSQL backup/restore contract;
- [`docs/redis-realtime-integration-v1.md`](docs/redis-realtime-integration-v1.md) — Redis distributed realtime baseline;
- [`docs/redis-recovery-v1.md`](docs/redis-recovery-v1.md) — Redis restart/recovery contract;
- [`docs/redis-failover-v1.md`](docs/redis-failover-v1.md) — Redis Sentinel topology, promotion и failover recovery contract;
- [`docs/realtime-multiprocess-v1.md`](docs/realtime-multiprocess-v1.md) — real Uvicorn multi-process / rolling-restart contract;
- [`docs/realtime-backpressure-v1.md`](docs/realtime-backpressure-v1.md) — bounded per-socket outbound queues и slow-consumer isolation;
- [`docs/web-application-maturity-v1.md`](docs/web-application-maturity-v1.md) — PWA/offline shell и client lifecycle;
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — типовые проблемы;
- [`docs/roadmap.md`](docs/roadmap.md) — актуальная дорожная карта;
- [`CHANGELOG.md`](CHANGELOG.md) — история версий.

## Технологии

Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 CI baseline, Redis 7.2 CI baseline, WebSocket.

Frontend: Vue 3 SPA/PWA, Vite, Vue Router, Vuex, Axios.

SPA является первым клиентом; backend API и realtime contracts проектируются reusable для будущих Android/iOS клиентов.

## Ключевые правила

- `Account != Persona`.
- Reputation/achievements не дают permissions.
- Space moderator не является platform moderator.
- Деньги не покупают trust и moderation power.
- Gifts/support не являются рейтингом и не влияют на discovery/authority.
- Organic discovery сначала применяет privacy/eligibility, а затем ranking.
- Числовой discovery score не является публичным API и не показывается пользователю.
- PostgreSQL — источник истины; Redis — ephemeral realtime слой.
- Production realtime не должен молча переходить в process-local fallback.
- Redis outage/failover должен быть видимым, а recovery — происходить без обязательного process restart.
- Direct `REDIS_URL` остаётся поддерживаемым; production HA может использовать Redis Sentinel без изменения realtime domain contract.
- Ticket/presence/rate-limit/idempotency/pub-sub semantics проверяются на настоящем Redis при `DEBUG=False`.
- Sentinel promotion проверяется на реальных Redis master/replica/Sentinel process, включая PubSub recovery и bounded concurrency после promotion.
- Multi-process WebSocket/rolling-restart semantics проверяются на реальных Uvicorn process в CI.
- Production listener принадлежит systemd socket unit и не должен исчезать при routine application deploy/restart.
- Routine backend deploy использует rolling worker reload; frontend build публикуется только после успешной staged сборки.
- Realtime fan-out не ждёт медленный socket write: каждый WebSocket имеет bounded outbound queue, а slow consumer изолированно отключается.
- Clean migration correctness проверяется на реальной PostgreSQL в CI; `create_all()` не заменяет Alembic rehearsal.
- Backup не считается рабочим, пока restore не проверен отдельной БД, schema-drift gate и semantic data assertions.
- Synthetic legacy/recovery fixtures не заменяют rehearsal на production-like snapshot.
- Access JWT браузера хранится только в памяти; долговременная сессия — HttpOnly refresh-cookie.
- Credentials не передаются в WebSocket URL.
- PWA service worker кэширует только shell/static assets и не является хранилищем auth/private API data.
- Reminder worker запускается внешним scheduler'ом и не живёт внутри FastAPI web-worker lifecycle.
- Standalone backend processes явно инициализируют ORM model registry.
- Offline external message re-engagement относится только к Messenger; Space chat не создаёт фоновый spam отсутствующему Account.
- Activity reminders остаются opt-in; browser/native push добавляется отдельным delivery adapter.
- Creator support — бесплатные internal cosmetic gestures; реальные payments требуют отдельного financial/security review.
