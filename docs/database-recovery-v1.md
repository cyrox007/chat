# Database recovery v1

Этот документ фиксирует проверенный recovery baseline Stage 6.1, выпущенный в `0.6.1-alpha.1`.

## Что проверяет CI

Recovery drill выполняется после clean migration gate и synthetic legacy migration rehearsal:

1. отдельная `chat_legacy_ci` уже находится на current Alembic head и содержит migrated representative legacy data;
2. PostgreSQL 16 `pg_dump` создаёт custom-format backup;
3. backup создаётся с `--no-owner --no-privileges`, чтобы restore не зависел от исходных owner/ACL;
4. создаётся отдельная пустая `chat_restore_ci`;
5. PostgreSQL 16 `pg_restore` восстанавливает backup в новую database;
6. restored DB должна находиться на current Alembic head;
7. `alembic check` не должен находить schema/model drift;
8. те же semantic assertions повторно проверяют Account/Persona/Credential/role backfill, Space settings/memberships/tags и legacy-ban behavior уже после restore.

Dump/restore client намеренно запускается из `postgres:16`, той же major-версии, что и CI database service. Это устраняет зависимость от версии PostgreSQL client, предустановленной на runner.

## Что этот gate доказывает

- custom-format PostgreSQL backup создаётся и не пуст;
- schema, Alembic revision и данные переживают restore в новую database;
- восстановленная schema согласована с ORM metadata;
- восстановленные legacy-derived данные сохраняют проверяемую business semantics;
- recovery flow не требует сохранения исходного database owner/ACL.

## Что этот gate не доказывает

CI recovery drill не является полной production backup policy. До beta/production отдельно нужны:

- rehearsal на anonymized production-like snapshot;
- правила retention и ротации database backup;
- отдельная проверка lifecycle private moderation media backup/snapshot copies;
- encryption at rest/in transit для backup artifacts;
- off-site/object-storage location и access control;
- измеренные RPO/RTO;
- restore rehearsal на объёме, близком к production;
- backup strategy для uploads/object storage;
- секреты вне database/repository backup;
- documented incident/recovery ownership.

## Production-oriented sequence

Для значимого deployment рекомендуемый порядок остаётся таким:

1. создать проверяемый backup до migration;
2. убедиться, что backup artifact записан в разрешённое durable storage;
3. выполнить migration rehearsal на копии актуальной schema/data;
4. применить `alembic upgrade head`;
5. проверить application smoke;
6. при recovery использовать новую/очищенную target database и совместимый PostgreSQL client;
7. после restore проверить Alembic revision, schema drift и критичные data invariants до открытия трафика.

## Invariants

- backup не считается рабочим, пока restore не был проверен;
- recovery test восстанавливает в отдельную database, а не поверх source;
- recovery correctness включает data assertions, а не только успешный exit code `pg_restore`;
- synthetic recovery drill не подменяет production-like recovery rehearsal;
- database backup не включает secrets и не решает backup для uploaded media;
- `ops/check-moderation-storage-lifecycle.sh` проверяет только declared private-media lifecycle limits и не заменяет provider-side lifecycle configuration.
