# PubChat

PubChat — SPA-приложение для свободного общения и живых тематических сообществ. Пользователь создаёт Persona, входит в Living Spaces, общается в realtime, участвует в событиях и активностях, строит социальные связи и управляет приватностью.

Проект не является копией Galaxy: PubChat развивает собственную концепцию без покупки социального влияния и без тюремной терминологии.

## Статус

Текущий выпущенный checkpoint: `0.5.3-alpha.1`.

Следующая development-линия: `0.5.4-alpha.0` — Discovery quality.

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
- [`docs/operations.md`](docs/operations.md) — эксплуатация;
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — типовые проблемы;
- [`docs/roadmap.md`](docs/roadmap.md) — актуальная дорожная карта;
- [`CHANGELOG.md`](CHANGELOG.md) — история версий.

## Технологии

Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis, WebSocket.

Frontend: Vue 3 SPA, Vite, Vue Router, Vuex, Axios.

SPA является первым клиентом; backend API и realtime contracts проектируются reusable для будущих Android/iOS клиентов.

## Ключевые правила

- `Account != Persona`.
- Reputation/achievements не дают permissions.
- Space moderator не является platform moderator.
- Деньги не покупают trust и moderation power.
- Gifts/support не являются рейтингом и не влияют на discovery/authority.
- PostgreSQL — источник истины; Redis — ephemeral realtime слой.
- Access JWT браузера хранится только в памяти; долговременная сессия — HttpOnly refresh-cookie.
- Credentials не передаются в WebSocket URL.
- Activity reminders в `0.5.2+` — opt-in in-app notifications; browser/native push появится отдельным delivery adapter позже.
- Creator support в `0.5.3` — бесплатные internal cosmetic gestures; реальные payments требуют отдельного financial/security review.
