# PubChat release checklist

## До version bump

- scope заморожен, P0/P1 blockers отсутствуют;
- migrations reviewed, `alembic heads` показывает одну head;
- backend compile/import и contract tests проходят;
- для DB-sensitive slice clean PostgreSQL `alembic upgrade head` проходит;
- `alembic check` не показывает model/schema drift;
- PostgreSQL integration smoke проходит там, где slice затрагивает persistence/worker behavior;
- frontend production build проходит;
- privacy/permissions/data self-review завершён;
- пользовательская и техническая документация обновлена;
- CI зелёный на exact functional head.

## Versioned gate

Только после первого успешного gate:

- обновить `VERSION`;
- зафиксировать release entry в `CHANGELOG.md`;
- синхронизировать versioning docs;
- снова запустить CI на exact versioned head;
- проверить совпадение backend/frontend версии;
- только после второго зелёного gate переводить PR в ready и merge.

## Перед deployment

- backup данных;
- migration rehearsal для рискованных изменений на репрезентативной копии schema/data;
- проверить PostgreSQL/Redis/configuration;
- собрать frontend;
- проверить `/health` и `/service/version`;
- выполнить smoke test login/session, Space realtime и DM.
- если email/Web Push delivery включены — проверить `python -m workers.external_delivery_observability --window-hours 24 --require-healthy` и разобрать stale backlog/expired claims до открытия трафика;

Clean-database migration CI не заменяет backup/restore drill и rehearsal на legacy data перед реальным production deployment.

Переход alpha → beta → stable зависит от readiness gate, а не даты или числа commits.
