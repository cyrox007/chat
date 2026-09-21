# Trust & Safety incident rehearsal v1

Этот playbook фиксирует минимальный операционный rehearsal для Stage 6.8. Он не заменяет production incident response, но не позволяет считать moderation stack готовым только потому, что отдельные endpoints работают.

## Инварианты

1. Один report может одновременно принадлежать только одному moderator claim.
2. Evidence открывается только владельцу claim и каждое открытие аудируется.
3. AI остаётся advisory-only: provider failure не должен менять moderation state, а structured recommendation не может содержать account.access.
4. Appeal рассматривается независимо; overturn снимает restriction, но не стирает историю.
5. Capability restriction живёт на Account, поэтому смена Persona не создаёт обход.
6. Behavioral signals по умолчанию только evidence. Protective holds выключены по умолчанию.
7. При явном включении protective holds:
   - один signal никогда не достаточен;
   - нужны как минимум два отдельных high/critical server-owned signal bucket в bounded lookback;
   - разрешены только messenger.send и invitation.send;
   - hold длится 5–15 минут и всегда имеет expiry;
   - moderator/admin/другая privileged role исключены;
   - account.access, permanent sanctions, media quarantine/remove, revoke и appeal decisions автоматике запрещены.
8. Operational metrics агрегированы: endpoint не возвращает Account ID, source UID, report text, message body или attachment metadata.

## Rehearsal matrix

| Сценарий | Ожидаемый результат | CI coverage |
| --- | --- | --- |
| Два модератора одновременно claim-ят report | ровно один claim успешен | test_trust_safety_postgres_integration.py |
| Evidence view | только claim owner; audit event обязателен | test_trust_safety_postgres_integration.py |
| AI recommendation | advisory schema; account.access невозможен | test_moderation_ai_contract.py / test_moderation_ai_postgres_integration.py |
| AI provider outage | 503 + audit; claim сохраняется; recommendation/restriction не создаются | test_moderation_ai_postgres_integration.py |
| Independent appeal overturn | restriction revoked, history сохранена | test_platform_restriction_appeals_postgres_integration.py |
| account.access | sessions revoked; Safety/appeal contour остаётся | test_account_access_postgres_integration.py |
| Abuse signal reviewed | review не создаёт restriction | test_abuse_signal_postgres_integration.py |
| Protective automation disabled | никакой restriction не создаётся | test_trust_safety_operations_postgres_integration.py |
| Повторные high-risk signals при явном enable | только короткий allow-listed hold | test_trust_safety_operations_postgres_integration.py |
| Privileged target | automated hold запрещён | test_trust_safety_operations_postgres_integration.py |
| Operations metrics | только aggregate values, без subject identifiers | test_trust_safety_operations_postgres_integration.py |
| Reported media quarantine/restore/remove | reversible filesystem state + audit | test_moderation_media_postgres_integration.py |
| Retention due while report active | bytes сохраняются; cleanup deferred | test_moderation_media_retention_postgres_integration.py |
| Retention due with pending linked appeal | bytes сохраняются; cleanup deferred | test_moderation_media_retention_postgres_integration.py |
| Appeal/report finality after old due date | полный retention window продлевается от latest finality | test_moderation_media_retention_postgres_integration.py |
| Evidence expiry | private bytes удалены, file metadata scrubbed, audit сохранён, повторный run идемпотентен | test_moderation_media_retention_postgres_integration.py |
| Retention path corruption/traversal | worker не может удалить sibling/out-of-root file | test_moderation_media_contract.py |

## Операционный порядок при инциденте

1. Проверить queue age и backlog signals.
2. При массовом abuse сначала использовать rate limits и human-reviewed signals.
3. Не включать protective holds только из-за одного инцидента: сначала подтвердить, что thresholds соответствуют наблюдаемому abuse и не дают неприемлемых false positives.
4. Если protective holds включаются, зафиксировать изменение конфигурации и отслеживать число active automation holds, appeal rate и moderator feedback.
5. При подозрении на false positives выключить MODERATION_PROTECTIVE_HOLDS_ENABLED. Уже созданные holds истекут самостоятельно не позднее configured maximum 15 минут.
6. Серьёзные действия выполняются только human policy path: account.access, permanent restrictions, media removal, appeal resolution.
7. После инцидента сохранить только агрегированные выводы/threshold changes; не переносить private evidence в свободные operational notes.
8. Перед ручным storage cleanup проверить due private evidence, active reports и pending appeals; application worker остаётся source of truth для record-level expiry.

## Beta gate

Protective holds не должны становиться enabled-by-default до накопления human-reviewed данных и явного решения Trust & Safety о приемлемом false-positive rate. Наличие реализации не означает разрешение автоматического punitive режима.

Private moderation evidence retention считается operationally complete только если production snapshots/backups имеют согласованный lifecycle: application-level unlink сам по себе не гарантирует forensic deletion из storage-layer copies.
