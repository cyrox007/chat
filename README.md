# PubChat

PubChat — SPA-приложение для свободного общения и живых тематических сообществ. Пользователь создаёт Persona, входит в Living Spaces, общается в realtime, участвует в событиях и активностях, строит социальные связи и управляет приватностью.

Проект не является копией Galaxy: PubChat развивает собственную концепцию без покупки социального влияния и без тюремной терминологии.

## Статус

Release candidate текущей ветки: `0.6.10-alpha.1`. Последний уже выпущенный `main` checkpoint остаётся `0.6.9-alpha.1` до exact-head CI и merge PR #30.

Текущая development-линия: `0.6.x-alpha` — Pre-beta hardening продолжается.

Stage 6 уже закрепил PostgreSQL 16 migration/integration/recovery baseline, Redis 7.2 distributed realtime, restart/recovery и real Sentinel master-promotion baseline, real multi-process Uvicorn/WebSocket rehearsal с rolling restart, bounded per-socket backpressure, message-notification delivery policy с distributed active-context suppression, durable unread-Messenger email delivery и standards-based Web Push/PWA Messenger delivery. Production backend запускается за постоянным systemd-owned listener, routine deploy меняет workers rolling reload без намеренного `502` окна, а frontend публикуется staged/asset-first.

Trust & Safety checkpoint `0.6.10-alpha.1` добавляет отдельный platform report/triage/evidence контур, Account-level иерархию moderation authority, capability restrictions с server-side enforcement, target-visible reason/scope/expiry и независимый appeal flow. Рабочие ограничения уже покрывают отправку Messenger/Space сообщений, messaging-media, создание/вступление/приглашения Spaces, редактирование Persona и публикацию owner-led Spaces в organic discovery. `account.access` намеренно ещё не выдаётся: полный suspension требует end-to-end session/HTTP/realtime enforcement и сохранения доступа к Safety Center/appeal/logout.

AI moderation зафиксирован как copilot: он может помогать triage, evidence summary и рекомендациями, но не является источником punitive authority в beta baseline. Следующий Trust & Safety слой — full Account suspension semantics, затем provider-neutral AI assessment storage/adapter, anti-spam/raid signals, moderation metrics/privacy-retention и incident rehearsal.

Message delivery различает online presence и активный conversation/Space: лишний toast/sound подавляется, если пользователь уже смотрит тот же context. Offline external re-engagement разрешён только для Messenger по opt-in. Для давно отсутствующего Account email worker создаёт агрегированное privacy-safe напоминание по durable ledger/cooldown/retry contract, а Web Push может доставить privacy-minimal уведомление на явно подписанное устройство. Space chat по-прежнему не создаёт background notification pressure отсутствующему Account.

До beta всё ещё нужны full Account access suspension semantics, AI-assisted moderation layer и anti-abuse/metrics/retention gates, rehearsal на anonymized production-like snapshot, member-capacity concurrency/DST hardening, observability, security и финальные accessibility/browser/operations gates. Параллельно формализуются cost model и monetization boundaries, чтобы infrastructure/moderation не зависели от бессрочного ручного финансирования.

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
- [`docs/operations.md`](docs/operations.md) — эксплуатация и background workers;
- [`docs/production-deploy-v1.md`](docs/production-deploy-v1.md) — persistent listener, staged SPA publish и health-gated rolling deploy;
- [`docs/message-notification-delivery-v1.md`](docs/message-notification-delivery-v1.md) — online/offline message routing, active context и external delivery policy;
- [`docs/message-email-delivery-v1.md`](docs/message-email-delivery-v1.md) — durable unread-Messenger email queue/provider/retry/systemd contract;
- [`docs/web-push-delivery-v1.md`](docs/web-push-delivery-v1.md) — per-device Web Push/VAPID/service-worker/provider/privacy contract;
- [`docs/trust-safety-v1.md`](docs/trust-safety-v1.md) — hierarchical platform moderation, capability restrictions, enforcement/appeals и AI-copilot boundaries;
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

Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 CI baseline, Redis 7.2 CI baseline, WebSocket, Web Push/VAPID.

Frontend: Vue 3 SPA/PWA, Vite, Vue Router, Vuex, Axios, Service Worker/Push API.

SPA является первым клиентом; backend API и realtime contracts проектируются reusable для будущих Android/iOS клиентов.

## Ключевые правила

- `Account != Persona`.
- Reputation/achievements не дают permissions.
- Space moderator не является platform moderator.
- Platform moderation authority определяется server-side RBAC + explicit authority hierarchy; actor не может ограничить Account с равным или более высоким authority.
- Platform sanctions ограничивают конкретные capabilities и считаются работающими только там, где есть реальный server-side enforcement point.
- Permanent sanctions требуют повышенного permission; `account.access` не выдаётся до полного suspension/recovery/appeal enforcement.
- AI moderation — copilot, а не самостоятельный punitive authority в beta baseline.
- Деньги не покупают trust и moderation power.
- Gifts/support не являются рейтингом и не влияют на discovery/authority.
- Organic discovery сначала применяет privacy/eligibility/moderation eligibility, а затем ranking.
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
- Active context используется только для notification UX и никогда не расширяет/сужает message authorization.
- Offline external message re-engagement относится только к Messenger и требует opt-in; Space chat не создаёт фоновый spam отсутствующему Account.
- Durable external delivery state хранится в PostgreSQL; destination email и private message text не сохраняются в delivery ledger.
- Email и Web Push workers запускаются внешним scheduler/systemd timer и не живут внутри FastAPI web-worker lifecycle.
- Web Push payload не содержит private message body/sender identity, а VAPID private key остаётся backend-only.
- Browser notification permission запрашивается только после явного user gesture; logout/session teardown отвязывает local push subscription best-effort.
- Clean migration correctness проверяется на реальной PostgreSQL в CI; `create_all()` не заменяет Alembic rehearsal.
- Backup не считается рабочим, пока restore не проверен отдельной БД, schema-drift gate и semantic data assertions.
- Synthetic legacy/recovery fixtures не заменяют rehearsal на production-like snapshot.
- Access JWT браузера хранится только в памяти; долговременная сессия — HttpOnly refresh-cookie.
- Credentials не передаются в WebSocket URL.
- PWA service worker кэширует только shell/static assets и не является хранилищем auth/private API data.
- Standalone backend processes явно инициализируют ORM model registry.
- Activity reminders остаются opt-in; external email/Web Push delivery добавляется отдельными adapters.
- Creator support — бесплатные internal cosmetic gestures; реальные payments требуют отдельного financial/security review.
