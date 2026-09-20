# Trust & Safety v1 — иерархическая модерация и AI-copilot

Этот документ фиксирует целевую модель модерации PubChat для Stage 6.8. Она расширяет существующие Space-local `ModerationReport` / `ModerationAction` / `ModerationAppeal` и platform Trust & Safety queue, но не смешивает локальные полномочия Space с глобальной властью платформы.

## Основная идея

Модерация PubChat состоит из трёх отдельных частей:

1. **Report / evidence** — пользователь или система сообщает о потенциальном нарушении, а платформа фиксирует минимально необходимый контекст.
2. **Human moderation authority** — Account с платформенной moderation role может применять только те ограничения, которые разрешены его ролью, и только к Account с меньшим authority level.
3. **AI moderation copilot** — AI помогает triage, суммированием контекста, поиском связанных сигналов и предложением решения, но не является источником полномочий и не заменяет человека в punitive decision path.

`Reputation != Role != Moderation Power`. Authority выдаётся только server-side RBAC и не зависит от донатов, подписки, подарков, достижений или discovery score.

## Реализованный AI-copilot checkpoint

В `0.6.13-alpha.1` AI-copilot реализован как отдельный advisory слой поверх human moderation:

- assessment доступен только модератору с `moderation.platform.ai.assess` и только для report, который уже находится в его claim;
- provider-neutral adapter получает только пожалованный объект; Account identifiers, handles, sender/recipient identity, unrelated private-dialog history, attachment URLs и свободное описание reporter не отправляются;
- ответ provider обязан соответствовать строгой structured schema: category, severity, confidence, summary, rationale и необязательное bounded temporary restriction suggestion;
- `account.access`, permanent sanctions, revoke и appeal decision AI предложить или выполнить не может;
- raw prompt, raw provider response и chain-of-thought не сохраняются;
- на report действует ограниченный assessment budget, чтобы AI не превращался в бесконтрольный расход внешнего provider;
- moderator UI фиксирует human outcome как `accepted`, `modified`, `rejected` или `not_used`; даже accepted suggestion только заполняет черновик, а применение санкции идёт через обычный human restriction API с hierarchy/permission checks.


## Реализованный anti-spam / raid signal checkpoint

В `0.6.14-alpha.1` добавлен durable behavioral signal layer. Его задача — дать модератору ранние server-owned признаки злоупотребления, не превращая эвристику в автоматический приговор.

- realtime rate-limit pressure в Messenger и Space создаёт deduped signal;
- Messenger detector считает distinct recipients в bounded window и сигнализирует о массовых DM-контактах;
- Space invitation detector считает distinct invitees в bounded window и сигнализирует о invite-spam pressure;
- signal хранит только account reference, тип surface/signal, counters, threshold/window metadata и review state; текст сообщений, история приватного диалога и attachment URLs туда не попадают;
- один signal можно отметить как `reviewed` или `dismissed`, но это не создаёт restriction;
- thresholds конфигурируемые: product/Trust & Safety команда должна калибровать их по реальным false-positive/false-negative данным, а не воспринимать default как универсальную норму;
- автоматическая санкция по одному behavioral signal запрещена baseline-контрактом. Для punitive action требуется обычный human moderation path с hierarchy, permissions, audit и appeal.

## Реализованный reported-media moderation checkpoint

В `0.6.15-alpha.1` добавлен отдельный human-only workflow для пожалованных локальных вложений.

- действие доступно только actor с `moderation.platform.media.manage`, который владеет claim на report и имеет authority выше target Account;
- поддерживаются только локальные `/uploads` attachments из Messenger/Space evidence; внешние URL и traversal paths отклоняются;
- quarantine физически переносит файл из публичного uploads tree в private moderation storage и ставит server-side moderation marker;
- restore возвращает quarantined файл обратно и снимает marker;
- remove оставляет файл вне публичной выдачи, но сохраняет private evidence copy до применения отдельной retention/deletion policy;
- private storage path никогда не возвращается frontend/API projection;
- filesystem move работает и при разных mount/filesystem через copy+unlink fallback; DB rollback пытается компенсировать filesystem move, сохраняя evidence copy при невозможности обратного переноса;
- каждое действие пишется в Trust & Safety audit как `media_quarantined`, `media_restored` или `media_removed`;
- AI copilot и anti-abuse automation не имеют права выполнять эти punitive media actions.

Retention baseline этого checkpoint сознательно conservative: evidence copy не удаляется автоматически. Secure deletion/expiry будет добавлена отдельным policy slice вместе с moderation privacy-retention metrics и incident rehearsal.

## Иерархия платформенных ролей

`PlatformRole` имеет явный `authority_level`. При нескольких ролях эффективный уровень Account — максимальный уровень его активных platform roles.

Начальный baseline:

| Role | Authority level | Назначение |
| --- | ---: | --- |
| `user` | 0 | обычный пользователь |
| `moderator` | 50 | platform Trust & Safety moderator |
| `admin` | 100 | platform administrator / highest current authority |

Числа являются внутренней policy-механикой, не social score и не показываются как репутация.

Правило применения санкции:

- actor должен иметь требуемый moderation permission;
- `actor_authority > target_authority`;
- actor не может ограничить самого себя;
- Space moderator без platform role не получает platform authority;
- одна Persona не позволяет обойти restriction: platform restrictions применяются к `Account`;
- изменение роли target после выдачи санкции не стирает audit trail и не делает старое решение несуществующим.

Иерархия не заменяет permissions. Например, высокий authority level сам по себе не даёт права на permanent restriction или `account.access`, если соответствующий permission отсутствует.

## Разделение platform moderation permissions

Начиная с checkpoint `0.6.12-alpha.1`, доступ к Trust & Safety queue и punitive authority разделены явно. `moderation.platform.manage` означает право войти в platform moderation surface, но сам по себе больше не должен давать право применять или отменять санкции.

Первая action-permission taxonomy:

| Permission | Назначение | Baseline moderator | Admin |
| --- | --- | --- | --- |
| `moderation.platform.manage` | доступ к platform Trust & Safety queue/context | да | да |
| `moderation.platform.restrict` | выдача обычных temporary capability restrictions | да | да |
| `moderation.platform.revoke` | прямое снятие restrictions в пределах hierarchy | да | да |
| `moderation.platform.appeal.review` | claim/review platform restriction appeals | да | да |
| `moderation.platform.permanent` | выдача/review/revoke бессрочных restrictions | нет | да |
| `moderation.platform.account_access` | выдача/review/revoke full Account suspension | нет | да |

Backend проверяет эти права повторно на action boundary; скрытие кнопки во frontend не является security control.

### Правила выдачи restriction

Для любого punitive action одновременно требуются:

1. `moderation.platform.manage`;
2. `moderation.platform.restrict`;
3. `actor_authority > target_authority`;
4. дополнительные elevated permissions для sensitive action.

Для `expires_at = NULL` дополнительно требуется `moderation.platform.permanent`. Для `account.access` дополнительно требуется `moderation.platform.account_access`; эта capability остаётся только platform-scoped.

### Правила прямого revoke

Снять активную санкцию недостаточно просто потому, что текущий actor выше target. Требуются:

- `moderation.platform.manage`;
- `moderation.platform.revoke`;
- текущий `actor_authority > target_authority`;
- текущий `actor_authority >= restriction.actor_authority_level`, сохранённого в момент исходного решения;
- для permanent sanction — `moderation.platform.permanent`;
- для `account.access` — `moderation.platform.account_access`.

Таким образом moderator может исправить temporary решение другого moderator того же authority, но не может отменить sanction, выданную admin. Пересмотр более сильного решения должен выполняться actor с не меньшей authority либо через соответствующий appeal-review path.

## Capability restrictions вместо одного общего ban

Основной механизм — ограничение конкретных возможностей Account. Это позволяет не блокировать весь аккаунт там, где достаточно точечной санкции.

Первая capability taxonomy:

- `messenger.send` — отправка новых личных сообщений;
- `space.chat.send` — отправка сообщений в Spaces;
- `media.upload` — загрузка медиа/вложений;
- `space.create` — создание новых Spaces;
- `space.join` — вступление в новые Spaces;
- `invitation.send` — отправка приглашений;
- `profile.edit` — изменение публичной Persona;
- `discovery.publish` — появление в органическом discovery;
- `account.access` — полный platform suspension/ban; наиболее сильная санкция.

Capability list расширяется только вместе с явными enforcement points и tests. Наличие строки в БД без проверки в domain service не считается работающей санкцией.

## Scope

Restriction имеет scope:

- `platform` — действует по всей платформе;
- `space` — действует только в одном Space;
- в будущем возможны более узкие scopes, если появится доказанная необходимость.

`account.access` является только platform-scoped capability. Попытка создать её с Space scope отклоняется уже schema boundary и дополнительно проверяется service layer.

Space-local moderation продолжает использовать Space membership/role rules. Platform moderator может применять platform restrictions только через Trust & Safety контур и не наследует автоматически права owner/moderator внутри конкретного Space.

## Срок

Каждое ограничение содержит `starts_at` и `expires_at`:

- `expires_at` с датой — временная санкция;
- `expires_at = NULL` — бессрочная санкция;
- permanent restriction требует отдельного более сильного permission/policy;
- expired/revoked restriction остаётся в audit history;
- снятие санкции создаёт отдельное audit event, а не переписывает прошлое.

Поддерживаются предупреждения без capability restriction, но они тоже имеют reason/audit linkage.

## Проверка санкции в runtime

Restriction enforcement выполняется server-side на границе domain action. Frontend только отражает состояние и объяснение.

Базовый внутренний enforcement API:

```python
await moderation_policy.assert_allowed(
    db,
    account_uid,
    capability="messenger.send",
    scope_type="platform",
    scope_uid=None,
)
```

Перед выполнением чувствительного действия service запрашивает активные restrictions. UI-disable без server check не является security control.

Для часто вызываемых realtime paths в будущем допустим краткоживущий Redis cache, но PostgreSQL остаётся durable source of truth; revoke/issue должен invalidatе cache. В текущем `account.access` path authoritative check выполняется непосредственно по PostgreSQL.

## Full Account suspension — `account.access`

`account.access` — не обычный UI-ban. Он закрывает Account по нескольким независимым границам, чтобы старый токен, другая Persona или уже открытый socket не обходили решение.

При выдаче restriction:

- capability доступна только actor с `moderation.platform.restrict`, `moderation.platform.account_access` и достаточным authority;
- существующие Identity v2 sessions получают `revoked_at` в той же DB-транзакции, что и durable restriction;
- legacy device sessions деактивируются там, где существует legacy identity bridge;
- после commit публикуется distributed realtime control event, закрывающий уже открытые Messenger/Space sockets на всех workers;
- если Redis недоступен, sanction не откатывается: PostgreSQL остаётся authoritative, а realtime уже работает в degraded/fail-closed режиме.

После выдачи:

- каждый authenticated HTTP request повторно проверяет active `account.access`, поэтому ещё живой stateless access JWT не является обходом;
- обычный `/realtime/v2/tickets` недоступен через тот же HTTP guard;
- one-time ticket, выданный прямо перед sanction, повторно проверяется по PostgreSQL после ticket consume во время WebSocket auth;
- остальные capability guards рассматривают `account.access` как глобальный wildcard restriction;
- sibling/new Persona того же Account не меняет target restriction.

### Restricted Safety session

Полное suspension не должно лишать Account возможности понять решение и оспорить его. Поэтому login/refresh допускают создание **restricted session**, но global HTTP guard разрешает только минимальный контур:

- `GET /identity/v2/me` — bootstrap и получение `access_restriction`;
- `GET /trust-safety/v1/me/restrictions` — причина/scope/expiry/history;
- `POST /trust-safety/v1/restrictions/{restriction_uid}/appeals` — одна апелляция на конкретное restriction;
- `GET /trust-safety/v1/me/restriction-appeals` — состояние и результат апелляции;
- logout остаётся доступен как unauthenticated-cookie operation.

Остальные authenticated HTTP routes получают `403 account_access_restricted`. SPA переводит Account в отдельный Restricted Safety Center вместо обычного приложения.

После revoke или expiry старые отозванные sessions **не восстанавливаются**. Пользователь проходит нормальную повторную аутентификацию; это не позволяет resurrection старого refresh token.

## Trust & Safety action

Platform action хранит минимум:

- target Account;
- actor Account;
- source report, если действие связано с жалобой;
- capability;
- scope;
- reason code;
- human-readable explanation;
- starts/expires/revoked timestamps;
- authority level actor/target на момент решения либо достаточные audit references для его восстановления;
- origin: `human`, `system_protection` или иной явный machine origin.

Нельзя молча редактировать reason/duration задним числом. Исправление делается новым audit event/replacement action.

## AI moderation copilot

AI является **советником модератора**, а не ролью в hierarchy.

AI может:

- классифицировать report category/severity;
- подсвечивать spam/raid patterns и связанные reports;
- делать privacy-minimal summary evidence;
- отмечать противоречия и недостающий контекст;
- предлагать capability, scope и duration;
- объяснять, какие policy signals привели к рекомендации;
- приоритизировать queue, не скрывая исходные reports от человека.

AI assessment хранится отдельно от human action и содержит:

- model/provider identifier и policy version;
- generated_at;
- suggested category/priority/action/capability/duration;
- confidence как внутренний signal, не публичный social score;
- machine-readable reasons/signals;
- moderator outcome: accepted / modified / rejected / not_used.

### Что AI v1 не делает

В beta baseline AI не может самостоятельно:

- выдавать permanent restriction;
- блокировать `account.access`;
- ограничивать moderator/admin;
- отклонять appeal окончательно;
- повышать себе authority;
- превращать private message history в unrestricted moderator-visible dataset.

Если позже появятся автоматические защитные меры, они должны быть отдельным `system_protection` policy: короткий reversible hold, жёсткий maximum TTL, audit event и обязательная возможность human review. Это не считается human moderation action.

## Evidence и privacy

Жалоба не даёт модератору неограниченный доступ к переписке.

Для reported Messenger message evidence содержит только необходимый snapshot/reference вокруг конкретного объекта и минимальный bounded context, если он нужен policy. Любой дополнительный evidence access журналируется.

AI получает тот же или более узкий evidence envelope, что и human moderator. Нельзя отправлять AI-провайдеру весь Messenger history «на всякий случай».

## Appeals

Любая значимая временная или permanent platform restriction видна затронутому Account с понятной причиной и сроком.

Appeal:

- связан с конкретным action/restriction;
- reviewer должен иметь отдельный `moderation.platform.appeal.review`;
- не рассматривается тем же moderator, если доступен другой eligible reviewer;
- reviewer authority должна быть не ниже `restriction.actor_authority_level`, то есть уровня исходного решения;
- permanent appeal дополнительно требует `moderation.platform.permanent`;
- appeal на `account.access` дополнительно требует `moderation.platform.account_access`;
- overturn не удаляет исходное решение, а revoke-ит restriction и пишет audit event;
- AI может подготовить summary, но не является финальным appeal reviewer.

Discovery независимого reviewer ищет только Account, у которых действительно есть appeal-review permission и которые проходят sensitive-action authority checks. Один общий `moderation.platform.manage` больше не считается достаточным.

`account.access` сохраняет appeal path даже когда все обычные product routes закрыты.

## Enforcement hierarchy examples

- `moderator(50)` + restrict permission → `user(0)`: temporary restriction разрешён;
- `moderator(50)` → `moderator(50)`: запрещено;
- `moderator(50)` → `admin(100)`: запрещено;
- `admin(100)` → `moderator(50)`: возможно при соответствующем permission;
- `moderator(50)` с revoke permission может снять temporary sanction, выданную другим `moderator(50)`, если target ниже обоих;
- `moderator(50)` не может снять sanction, выданную `admin(100)`, даже если target — `user(0)`;
- Account с одним `moderation.platform.manage`, но без `moderation.platform.restrict/revoke/appeal.review`, может иметь queue access, но не punitive authority;
- Space moderator без platform role → обычный Account вне его Space: platform restriction запрещён;
- AI → любой Account: recommendation разрешена, punitive authority отсутствует.

## Implementation slices

1. ✅ Platform report intake/queue + append-only audit baseline.
2. ✅ Role hierarchy (`authority_level`) и server-side permission/authority resolver baseline.
3. ✅ Durable platform capability restrictions: scope, duration/permanent, revoke and enforcement API.
4. ✅ Enforcement hooks в Messenger/Space chat/uploads/invitations/Space creation/discovery/account session + HTTP/realtime path.
5. ✅ Human moderator action UX + target-visible explanation + restriction appeal linkage baseline.
6. ✅ Permission/hierarchy hardening: queue access отделён от issue/revoke/appeal-review; higher-authority decisions защищены от lower-authority revoke; permanent/account-access остаются elevated.
7. ⏳ AI assessment model + provider-neutral adapter + moderator recommendation UI.
8. ⏳ Anti-abuse automation signals и, только после отдельного review, optional short-lived system protection holds.
9. ⏳ Metrics, privacy/retention, incident rehearsal and launch gate.

## Beta gate

Trust & Safety считается beta-ready только если проходит end-to-end:

`report → triage/AI assist → human claim/review → hierarchy/permission check → restriction → runtime enforcement → audit → target notification → appeal → independent review/revoke/uphold`.

Human enforcement/appeal baseline уже существует, включая full Account suspension и explicit punitive permission boundaries. Следующие beta-critical риски — AI-assist boundary implementation, anti-abuse/metrics/retention и incident rehearsal.

Существование таблиц или AI-классификатора без реального server-side capability enforcement не считается готовой модерацией.
