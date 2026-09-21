# Trust & Safety private media retention v1

Этот документ задаёт privacy-retention policy для private evidence, созданного reported-media workflow.

## Область

Policy применяется только к `moderation_media_records` со статусом `removed`: файл уже исключён из публичного `/uploads`, но временно хранится как private moderation evidence.

`quarantined` evidence не удаляется retention worker, пока модератор ещё может восстановить файл. `restored` record не имеет private evidence copy.

## Retention window

Baseline по умолчанию — **90 дней**, конфигурируется через `MODERATION_MEDIA_REMOVED_RETENTION_DAYS` и жёстко ограничен диапазоном 7–365 дней.

Начальный `retention_due_at` выставляется при `remove`. Перед фактическим expiry worker пересчитывает safety anchor и гарантирует полный retention window после самой поздней из точек:

- `removed_at`;
- `TrustSafetyReport.resolved_at`;
- `resolved_at` последней связанной platform-restriction appeal.

Если новый anchor сдвигает срок вперёд, `retention_due_at` продлевается durable в БД.

## Что блокирует expiry

Даже после `retention_due_at` bytes не удаляются, если:

- report остаётся `triage`, `in_review` или `escalated`;
- у restriction, связанного с этим report, существует appeal со статусом `pending`.

Таким образом worker не удаляет evidence во время активного расследования или незавершённого пересмотра.

Новая appeal, созданная уже после фактического expiry, остаётся допустимой по текущему appeal contract, но raw media к этому моменту может больше не существовать. Appeal reviewer опирается на сохранённые decision/audit records. Если продукту понадобится гарантированная raw-evidence availability на весь срок возможной appeal, это требует отдельного appeal deadline/legal-hold policy, а не бессрочного скрытого хранения.

## Expiry

При наступлении срока worker:

1. проверяет record-scoped path confinement;
2. удаляет private file;
3. best-effort fsync-ит директорию;
4. очищает `private_relative_path`, `original_url`, `original_relative_path`, `original_name` и `mime_type`;
5. ставит `purged_at`;
6. сохраняет moderation decision, target/actor linkage, reason и timestamps;
7. пишет append-only `media_evidence_expired` в Trust & Safety audit.

Если файл уже отсутствует, это считается recoverable/idempotent состоянием: record всё равно переводится в purged metadata state с audit outcome `already_missing`.

## Storage boundary

`MODERATION_MEDIA_ROOT` обязан быть отдельным путём, не совпадающим и не пересекающимся как parent/child с публичным `uploads`.

Quarantine record directory получает mode `0700`, evidence file — `0600`; retention systemd unit запускается с `UMask=0077`.

Stored relative path обязан начинаться с собственного `record.uid`. Даже повреждённая строка БД не должна позволить worker удалить evidence другого record или файл за пределами private root.

## Что означает secure expiry

Worker реализует **application-level secure expiry**: bounded retention, path confinement, unlink, metadata scrub и audit.

Это **не является гарантией forensic secure wipe** на SSD, copy-on-write filesystem, RAID, snapshots, backup или provider-managed storage. Для таких копий production storage/backup должен иметь отдельный lifecycle/retention policy, согласованный с этим приложением.

## Worker

CLI:

```bash
cd backend
venv/bin/python3 -m workers.moderation_media_retention
```

Tracked deployment units:

- `ops/systemd/pubchat-moderation-media-retention.service`;
- `ops/systemd/pubchat-moderation-media-retention.timer`;
- `ops/install-moderation-media-retention-worker.sh`.

Timer запускает bounded batch ежедневно с randomized delay. Candidate rows claim-ятся через PostgreSQL `FOR UPDATE SKIP LOCKED`, поэтому несколько worker instances не должны одновременно обрабатывать один record.

## Crash/retry semantics

Filesystem и PostgreSQL не образуют общей транзакции.

- если unlink не удался, record не получает `purged_at`;
- если файл удалён, но DB commit завершился ошибкой/crash, следующий запуск увидит отсутствующий файл, scrub-ит metadata и завершит audit как `already_missing`;
- повторный успешный запуск после purge идемпотентен.

## Monitoring

Aggregate Trust & Safety metrics показывают:

- количество due removed evidence records;
- количество purged records в выбранном metrics window;
- configured retention days.

Metrics не возвращают file paths, Account IDs, report IDs или message contents.

## Beta gate

Перед beta необходимо:

- миграция schema проходит clean/legacy rehearsal;
- PostgreSQL integration подтверждает active-report deferral;
- pending appeal подтверждён как hard blocker;
- после appeal finality retention window продлевается полностью;
- purge удаляет bytes и file-locating metadata, но сохраняет audit;
- path traversal/cross-record deletion невозможны contract tests;
- production backup/snapshot retention не длиннее утверждённой privacy policy без отдельного обоснованного hold.
