# Pre-beta hardening v1

Этот документ фиксирует первый валидированный checkpoint линии Stage 6. Он не означает завершение pre-beta hardening целиком.

## Release checkpoint

Version: `0.6.0-alpha.1`.

Scope: PostgreSQL migration/integration baseline с synthetic representative pre-revival data rehearsal.

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
- DB URL строится через SQLAlchemy `URL.create()`, поэтому логин/пароль со специальными символами корректно кодируются;
- отдельная legacy rehearsal DB мигрируется до pre-revival revision `4f3d66790cd3`, засеивается synthetic representative legacy data и затем обновляется до current head;
- legacy rehearsal делает data assertions для Account/Persona/Credential/role backfill, Space settings/memberships/tags и активного legacy ban semantics;
- legacy rehearsal повторно проходит `alembic current` и `alembic check` после data-preserving upgrade.

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

- rehearsal на anonymized production-like snapshot/копии реальной legacy schema/data, а не только на synthetic fixture;
- backup/restore drill;
- расширенные before/after data assertions на production-like snapshot;
- member-capacity concurrency hardening под реальной PostgreSQL;
- IANA timezone storage и DST-correct recurring wall-clock semantics;
- destructive downgrade не является launch requirement и отдельно не обещается.

## Invariants

- одна Alembic head;
- schema changes не обходят migration chain через `create_all`;
- CI не отключает `alembic check` ради ложного green;
- исправления исторических migrations не должны менять уже определённую бизнес-семантику backfill;
- synthetic fixture не подменяет rehearsal на production-like snapshot;
- standalone workers обязаны явно инициализировать ORM registry;
- PostgreSQL остаётся authoritative persistent datastore.
