# PubChat

PubChat — SPA-приложение для свободного общения и живых тематических сообществ. Пользователь создаёт Persona, входит в Living Spaces, общается в realtime, участвует в событиях и активностях, строит социальные связи и управляет приватностью.

Проект не является копией Galaxy: PubChat развивает собственную концепцию без покупки социального влияния и без тюремной терминологии.

## Статус

Текущий выпущенный checkpoint: `0.6.1-alpha.1`.

Текущая development-линия: `0.6.x-alpha` — Pre-beta hardening продолжается.

Stage 6 уже закрепил PostgreSQL 16 CI, clean historical `alembic upgrade head`, zero `alembic check` drift, real async PostgreSQL smoke, synthetic representative legacy-data rehearsal и исполняемый PostgreSQL backup/restore recovery drill с повторными semantic data assertions.

До beta всё ещё нужны rehearsal на anonymized production-like snapshot, member-capacity concurrency/DST hardening, Redis/realtime reliability, observability, load/security и финальные accessibility/operations gates.

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
- [`docs/prebeta-hardening-v1.md`](docs/prebeta-hardening-v1.md) — Stage 6 PostgreSQL/migration hardening baseline;
- [`docs/database-recovery-v1.md`](docs/database-recovery-v1.md) — проверяемый backup/restore contract;
- [`docs/web-application-maturity-v1.md`](docs/web-application-maturity-v1.md) — PWA/offline shell и client lifecycle;
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — типовые проблемы;
- [`docs/roadmap.md`](docs/roadmap.md) — актуальная дорожная карта;
- [`CHANGELOG.md`](CHANGELOG.md) — история версий.

## Технологии

Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis, WebSocket.

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
- Clean migration correctness проверяется на реальной PostgreSQL в CI; `create_all()` не заменяет Alembic rehearsal.
- Backup не считается рабочим, пока restore не проверен отдельной БД, schema-drift gate и semantic data assertions.
- Synthetic legacy/recovery fixtures не заменяют rehearsal на production-like snapshot.
- Access JWT браузера хранится только в памяти; долговременная сессия — HttpOnly refresh-cookie.
- Credentials не передаются в WebSocket URL.
- PWA service worker кэширует только shell/static assets и не является хранилищем auth/private API data.
- Reminder worker запускается внешним scheduler'ом и не живёт внутри FastAPI web-worker lifecycle.
- Standalone backend processes явно инициализируют ORM model registry.
- Activity reminders остаются opt-in; browser/native push появится отдельным delivery adapter позже.
- Creator support — бесплатные internal cosmetic gestures; реальные payments требуют отдельного financial/security review.
