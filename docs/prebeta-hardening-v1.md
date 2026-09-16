# Pre-beta hardening v1

Этот документ фиксирует первый валидированный checkpoint линии Stage 6. Он не означает завершение pre-beta hardening целиком.

## Release checkpoint

Version: `0.6.0-alpha.1`.

Scope: production-like PostgreSQL migration/integration baseline.

## Что уже доказано CI

- backend CI поднимает реальный PostgreSQL 16 service;
- полная историческая цепочка `alembic upgrade head` проходит на чистой базе;
- `alembic current` достигает единственной head;
- `alembic check` показывает отсутствие model/schema drift;
- backend contract tests проходят после migration rehearsal;
- отдельный async PostgreSQL smoke открывает реальную SQLAlchemy AsyncSession;
- smoke проверяет наличие ключевых migrated tables и durable notification worker state;
- worker cursor успешно читается и блокируется через реальную PostgreSQL session;
- standalone worker использует явный ORM model registry вместо зависимости от случайного import order web-приложения;
- DB URL строится через SQLAlchemy `URL.create()`, поэтому логин/пароль со специальными символами корректно кодируются.

## Исправленный migration debt

### Identity v2 credential backfill

Историческая migration использовала raw SQL literals `:password`, `:email`, `:phone` внутри `op.execute()`. SQLAlchemy интерпретировал их как bind parameters, и clean migration падала до создания текущей схемы.

Исполнение трёх backfill statements переведено на `op.get_bind().exec_driver_sql(...)`. Сами deterministic salts и UUID formula не изменены.

### Metadata/schema reconciliation

`alembic check` выявил три расхождения:

- существующие unique constraint + unique index для `personas.handle`;
- существующие unique constraint + unique index для `identity_sessions.refresh_token_hash`;
- дублирующий `UniqueConstraint` поверх composite primary key `activity_rsvps(activity_uid, account_uid)`.

ORM metadata приведена к фактической уже выпущенной схеме без изменения пользовательских данных.

### Standalone ORM bootstrap

CLI worker раньше косвенно зависел от import side effects FastAPI composition root. При прямом ORM query SQLAlchemy mapper мог не найти legacy `User` relationship.

Добавлен единый model registry bootstrap, который явно регистрирует ORM graph и вызывает mapper configuration для non-web processes.

## Что этот checkpoint ещё не доказывает

Stage 6.1 остаётся активным. Следующие обязательные задачи:

- migration rehearsal на репрезентативной legacy schema/data, а не только на чистой БД;
- backup/restore drill;
- upgrade rehearsal с data assertions до/после;
- member-capacity concurrency hardening под реальной PostgreSQL;
- IANA timezone storage и DST-correct recurring wall-clock semantics;
- destructive downgrade не является launch requirement и отдельно не обещается.

## Invariants

- одна Alembic head;
- schema changes не обходят migration chain через `create_all`;
- CI не отключает `alembic check` ради ложного green;
- исправления исторических migrations не должны менять уже определённую бизнес-семантику backfill;
- standalone workers обязаны явно инициализировать ORM registry;
- PostgreSQL остаётся authoritative persistent datastore.
