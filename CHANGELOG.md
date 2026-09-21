# PubChat — история версий

Формат до стабильного релиза: `MAJOR.MINOR.PATCH-channel.N`.

## [0.6.21-alpha.1] — 2026-09-21

Stage 6 checkpoint 13 — UI motion/loading polish.

- RouterView получил мягкий out-in transition и delayed/min-visible navigation progress, чтобы быстрые маршруты не мигали, а lazy/data-heavy переходы имели понятный feedback;
- добавлены общие motion/state/popover/skeleton/spinner primitives с корректным `prefers-reduced-motion`;
- Create Space modal теперь плавно открывает backdrop/panel, на mobile ведёт себя как sheet, блокирует body scroll и показывает pending spinner при submit;
- persona dropdown и chevron получили плавное состояние открытия/закрытия;
- Messenger больше не показывает ложное empty-state до загрузки: добавлены skeleton списка, skeleton истории, error/retry и pending state открытия разговора;
- registration step, profile settings, Space discovery loading/error/results/empty и join actions получили мягкие transitions/pending feedback;
- login/profile/registration submit-кнопки показывают явный spinner/pending state;
- восстановлен корневой `update.sh` wrapper, делегирующий routine production update в `ops/deploy.sh`;
- functional exact-head CI #645 fully green: backend, frontend, dependency-security и Chromium/Firefox/WebKit/mobile browser-smoke.

Motion не должен замедлять приложение искусственно: progress появляется только после короткой задержки, а reduced-motion users получают практически мгновенные состояния.

## [0.6.20-alpha.1] — 2026-09-21

Stage 6 checkpoint 12 — browser/security launch gate.

- browser runtime contract теперь same-origin по умолчанию: SPA использует `/api`, а Vite dev/preview proxy передаёт HTTP и WebSocket трафик в backend без исторического `http://localhost:9000` fallback;
- CSRF усилен с cookie-only проверки до signed HttpOnly cookie + отдельного `X-CSRF-Token` proof, который SPA хранит только в памяти;
- unsafe API requests сами выполняют CSRF bootstrap, поэтому registration/login/refresh больше не зависят от mount-time race;
- full reload восстанавливает session через HttpOnly refresh cookie + новый CSRF proof, не записывая access token в local/session storage;
- добавлен Playwright launch gate для Chromium, Firefox, WebKit/Safari-compatible engine и narrow mobile Chromium;
- browser journey реально выполняет registration → refresh-after-reload → Messenger route → logout/revocation → login и проверяет cookie/session semantics;
- CI запрещает возврат cross-origin localhost API fallback в SPA source;
- production dependency gate теперь запускает `npm audit --omit=dev --audit-level=high` и `pip-audit`;
- frontend production lock обновлён до audit-clean набора; direct floors подняты для Axios, DOMPurify и UUID;
- backend security-sensitive dependencies обновлены; FastAPI/Starlette закреплены на audit-clean совместимой паре, сохраняющей текущий route contract;
- функциональный exact-head CI #637 полностью зелёный: dependency-security, frontend, backend/PostgreSQL/Redis/Sentinel/recovery и четыре browser projects.

Этот checkpoint закрывает автоматизированный desktop/WebKit auth/session launch gate, но не подменяет реальный iOS/iPadOS installed-PWA/device rehearsal и оставшиеся pre-beta performance/accessibility/production-data задачи.

## [0.6.19-alpha.1] — 2026-09-21

Stage 6 checkpoint 11 — privacy-safe external delivery observability baseline.

- email/Web Push получили агрегированные operational metrics по durable `external_delivery_ledger`: pending/due backlog, processing, expired claims, retry pressure, delivered/failed и failure classes;
- stale due backlog определяется отдельными alert thresholds для email и Web Push, не меняющими delivery behavior;
- admin-only endpoint `GET /admin/operations/external-delivery` отдаёт только агрегаты;
- standalone CLI `python -m workers.external_delivery_observability` печатает machine-readable report и поддерживает `--require-healthy` для внешнего monitoring;
- email queue/delivery и Web Push delivery workers получили structured JSON completion events;
- structured logger fail-closed отклоняет sensitive field names для tokens/secrets/passwords/destination email/push endpoints/key material/message body/content;
- PostgreSQL integration проверяет stale backlog + expired claim detection и отсутствие Account ID, aggregate/dedupe keys, claim token и provider id в metrics output;
- CI теперь отдельно запускает observability CLI machine gate;
- функциональный exact-head CI #608 прошёл frontend/backend, migrations/schema drift, PostgreSQL observability rehearsal, Redis/Sentinel, multi-process WebSocket, rolling reload, legacy migration и backup/restore.

Этот checkpoint закрывает ledger-side external-delivery visibility, но не объявляет готовым полный observability stack: provider-side SLA telemetry, общий HTTP/realtime/Redis/PostgreSQL metrics backend, error tracking и pager/on-call остаются отдельной pre-beta работой.

## [0.6.18-alpha.1] — 2026-09-21

Stage 6.8 checkpoint 9 — protective-hold shadow calibration and moderation storage lifecycle gate.

- protective holds получили явные режимы `off | shadow | enforce`; default остаётся `off`;
- `shadow` вычисляет would-hold решение и пишет privacy-minimal evaluation, но никогда не меняет user capabilities;
- добавлен durable `protective_hold_evaluations` ledger без message body, attachment URL, recipient list или Persona handle;
- moderator queue получила явные human labels `true_positive / false_positive / unclear`, не создающие restriction;
- aggregate calibration считает false-positive rate отдельно для DM burst и invite burst, а также ограниченный confirmed-candidate capture proxy;
- enforce fail-closed: каждый signal family должен набрать минимум human-labeled candidates и пройти FP threshold, после чего всё равно требуется отдельный `MODERATION_PROTECTIVE_HOLD_ENFORCEMENT_APPROVED=true`;
- legacy `MODERATION_PROTECTIVE_HOLDS_ENABLED=true` больше не является достаточным условием для санкции;
- standalone calibration CLI умеет печатать отчёт и завершаться non-zero, если data gate не готов;
- moderator operations dashboard показывает automation mode, calibration readiness/FP и storage-lifecycle status;
- private moderation evidence backup/snapshot retention теперь должен быть явно объявлен; production preflight отклоняет отсутствующие значения и сроки, превышающие application retention;
- retention-worker installer требует storage lifecycle declarations до включения timer;
- CI отдельно rehearses shadow-without-sanction, false-positive gate, approval gate, allow-listed enforcement и storage retention preflight;
- synthetic CI labels проверяют механику, но **не считаются production calibration data**.

Реальное включение protective holds после этого checkpoint всё ещё требует накопления human-reviewed production-like/production shadow data. Preflight также не настраивает provider lifecycle автоматически: заявленные backup/snapshot сроки должны соответствовать фактической инфраструктуре.

## [0.6.17-alpha.1] — 2026-09-21

Stage 6.8 checkpoint 8 — bounded private moderation evidence retention and application-level secure expiry.

- `moderation_media_records` получил durable `retention_due_at` / `purged_at` lifecycle и nullable file-locating metadata после expiry;
- removed evidence получает configurable retention baseline: 90 дней по умолчанию, жёстко ограниченный 7–365 днями;
- фактический expiry гарантирует полный retention window после самой поздней точки `removed_at`, final report resolution или завершения связанной restriction appeal;
- active Trust & Safety report и pending appeal блокируют deletion; deferred records фильтруются до bounded batch selection, чтобы они не starvation-или eligible evidence;
- private storage обязан быть disjoint от публичного `/uploads`; quarantine directory/file hardening использует 0700/0600, worker — `UMask=0077`;
- retention deletion confined к каталогу конкретного `record.uid`, включая запрет sibling-record traversal;
- expiry удаляет private bytes, scrub-ит private/original path, URL, filename и MIME metadata, но сохраняет moderation decision/reason/audit linkage;
- missing file на retry является idempotent recoverable state; worker завершает metadata scrub и audit outcome `already_missing`;
- отдельный systemd oneshot/timer запускает bounded `FOR UPDATE SKIP LOCKED` cleanup вне Uvicorn lifecycle;
- moderator operations metrics показывают только aggregate due/purged counts и configured retention days;
- документация явно отделяет application-level expiry от forensic secure wipe на SSD/COW/snapshots/backups;
- functional exact-head CI #595 green: frontend/backend contracts, PostgreSQL retention lifecycle, Redis/Sentinel, multi-process WebSocket, rolling reload, legacy migration и backup/restore.

Protective holds остаются выключенными по умолчанию. Следующий Trust & Safety шаг — production calibration на human-reviewed signals и согласование backup/snapshot lifecycle с утверждённой evidence retention policy.

## [0.6.16-alpha.1] — 2026-09-20

Stage 6.8 checkpoint 7 — Trust & Safety operations metrics, incident rehearsal and calibrated protective-hold baseline.

- добавлен privacy-minimal aggregate endpoint `/trust-safety/v1/metrics`: queue age, average decision time, appeal overturn rate, AI outcomes, behavioral-signal backlog и human/automation restriction origins без Account ID или содержимого жалоб;
- moderator UI показывает operational dashboard и текущий безопасный policy-status protective holds;
- protective holds существуют как отдельный low-risk automation path, но **выключены по умолчанию** до калибровки human-reviewed false-positive rate;
- один behavioral signal никогда не создаёт sanction: для hold нужны минимум два отдельных high/critical server-owned signal bucket в bounded lookback;
- automation allow-list ограничен только `messenger.send` и `invitation.send`; срок всегда 5–15 минут, permanent restriction невозможен;
- `account.access`, Space chat, media actions, profile/discovery powers, revoke и appeal decisions не входят в automation surface;
- privileged Account с platform authority исключён из automation path;
- Account-level `FOR UPDATE` сериализация не позволяет concurrent detectors создать дублирующий hold; каждое действие имеет audit event и может быть снято обычным human revoke/appeal path;
- provider outage AI-copilot отдельно rehearsed: failure аудируется, recommendation/restriction не создаются, claim state не меняется;
- добавлен `docs/trust-safety-incident-rehearsal-v1.md` с incident matrix и beta gate;
- functional exact-head CI #579 прошёл frontend/backend/PostgreSQL/Redis/Sentinel/WebSocket/legacy migration/backup-restore gates до release-doc sync.

Следующий отдельный Trust & Safety slice — формальная privacy-retention/secure-expiry policy для private moderation evidence и production calibration до возможного включения protective holds.

## [0.6.15-alpha.1] — 2026-09-20

Stage 6.8 checkpoint 6 — reversible reported-media moderation workflow.

- добавлен отдельный permission `moderation.platform.media.manage` для quarantine/restore/remove действий над пожалованными вложениями;
- `moderation_media_records` хранит durable audit-oriented state без публикации private evidence path клиенту;
- quarantine переносит локальный `/uploads` файл в приватное moderation storage и помечает attachment metadata server-side;
- restore возвращает файл и снимает moderation marker; remove оставляет его вне публичной выдачи, сохраняя evidence copy до применения retention policy;
- filesystem move поддерживает cross-device deployment и compensating rollback при ошибке DB commit;
- path confinement запрещает traversal и внешние URL;
- действия требуют claim ownership, explicit permission и authority выше target Account; AI/automation не получают punitive media authority;
- moderator UI показывает reported attachments и даёт явные quarantine/restore/remove controls с причиной действия;
- PostgreSQL/filesystem integration и contract tests покрывают reversible state, audit и cross-filesystem fallback.

## [0.6.14-alpha.1] — 2026-09-18

Stage 6.8 checkpoint 5 — privacy-minimal anti-spam / raid abuse signals.

- добавлен durable `trust_safety_abuse_signals` ledger для behavioral evidence без хранения message body, private-dialog transcript или attachment URLs;
- realtime Messenger/Space rate-limit pressure создаёт deduped advisory signal, но не автоматическую санкцию;
- Messenger detector отслеживает burst по distinct DM recipients в bounded window как признак массовых нежелательных контактов;
- Space invitation detector отслеживает burst по distinct invitees в bounded window как признак invite spam;
- thresholds/window/dedupe параметры конфигурируемые и ограничены безопасными минимумами;
- moderator API и Trust & Safety UI получили отдельную очередь behavioral signals со статусами open/reviewed/dismissed;
- review/dismiss signal не создаёт restriction и не меняет Account permissions: punitive path остаётся только human moderation flow;
- PostgreSQL integration проверяет durable dedupe/upsert, human review state и отсутствие side-effect restriction;
- Alembic/model registry/schema-drift интеграция синхронизирована.

## [0.6.13-alpha.1] — 2026-09-18

Stage 6.8 checkpoint 4 — provider-neutral moderation AI copilot.

- добавлен отдельный permission `moderation.platform.ai.assess`; доступ к Trust & Safety queue сам по себе не даёт права использовать AI provider;
- AI-copilot работает только с жалобой, уже взятой модератором в claim, и не имеет punitive authority;
- provider-neutral `http_json` adapter принимает строго структурированный assessment и валидирует ответ через Pydantic schema;
- provider payload privacy-minimal: только пожалованный Persona/message object; без Account UID, handle, sender/recipient identity, истории личного диалога, attachment URL и свободного текста описания жалобы;
- `account.access` исключён из AI suggestion schema; AI может предложить только bounded temporary restriction или отсутствие санкции;
- durable `moderation_ai_recommendations` хранит category/severity/confidence/summary/rationale и human outcome, но не raw prompt, raw provider response, chain-of-thought или private conversation history;
- на одну жалобу действует bounded assessment budget, по умолчанию 3 запроса, чтобы исключить бесконтрольное provider-cost amplification;
- moderator UI показывает AI severity/confidence/summary/rationale и позволяет явно принять предложение как черновик, взять его за основу для изменения либо отклонить; применение restriction всё равно идёт через обычный human moderation API и hierarchy/permission checks;
- provider failure аудируется и не меняет moderation state;
- Alembic/model registry синхронизированы; deterministic contract tests и PostgreSQL integration покрывают schema/privacy/persistence/audit/human-outcome boundaries.

## [0.6.12-alpha.1] — 2026-09-17

Stage 6.8 checkpoint 3 — fine-grained platform moderation permission hierarchy.

- доступ к Trust & Safety queue больше не означает автоматическое право выдавать, снимать и пересматривать санкции: добавлены отдельные `moderation.platform.restrict`, `moderation.platform.revoke` и `moderation.platform.appeal.review` permissions;
- baseline moderator получает обычные issue/revoke/appeal-review powers, а permanent restrictions и `account.access` по-прежнему требуют отдельных elevated permissions;
- restriction issuance требует одновременно platform moderation access, explicit issue permission и строгий `actor_authority > target_authority`;
- direct revoke требует отдельный revoke permission, authority выше target и authority не ниже snapshot исходного issuer, поэтому peer moderator не может отменить sanction более сильного admin;
- revoke permanent restriction и `account.access` дополнительно требует тех же elevated permissions, что нужны для чувствительного исходного решения;
- appeal review требует отдельного review permission плюс существующие authority/sensitivity checks; independent-review search учитывает только реально eligible reviewers;
- action endpoints переведены с generic moderator dependency на specific action dependencies, а capability discovery возвращает только те capabilities, которые текущий moderator действительно может выдать;
- миграция `k0a6d4f88010` после исторического explicit-ID seed синхронизирует sequence `platform_permissions_id_seq`, устраняя collision при clean migration;
- PostgreSQL integration проверяет denial для manage-only custom role, peer-moderator revoke, запрет override admin sanction, elevated permanent/account-access permissions и explicit appeal-review permission;
- moderator UI использует server-provided permission flags, чтобы не предлагать actor действия, которые backend всё равно отклонит.

Следующий Stage 6.8 slice — provider-neutral AI assessment / copilot layer; punitive authority остаётся только у human policy path.

Quality gate: functional exact-head CI #528 green before release-doc sync; final exact-head CI required before merge.

## [0.6.11-alpha.1] — 2026-09-17

Stage 6.8 checkpoint 2 — end-to-end `account.access` platform suspension.

- сильнейшая moderation capability `account.access` переведена из schema-only состояния в реальный server-side enforcement и разрешена только в platform scope;
- выдача suspension по-прежнему требует `moderation.platform.account_access`, обычного platform moderation permission и строгого `actor_authority > target_authority`;
- при выдаче ограничения существующие Identity v2 sessions отзываются в той же транзакции, legacy device sessions деактивируются;
- короткоживущий stateless access JWT не позволяет обойти suspension: каждый authenticated HTTP request повторно проверяет durable PostgreSQL restriction;
- доступ под suspension ограничен минимальным Safety-контуром: identity bootstrap, просмотр собственного ограничения, создание/просмотр своей апелляции и logout;
- login/refresh могут создать restricted session, чтобы Account не терял право узнать причину санкции и подать апелляцию;
- realtime ticket re-check выполняется после consume one-time ticket, закрывая гонку «ticket выдан непосредственно перед suspension»;
- уже открытые Messenger/Space WebSocket соединения отключаются distributed `account_control` событием во всех Uvicorn workers; Redis transport failure не отменяет durable sanction;
- SPA получила отдельный restricted Safety Center с причиной, сроком, appeal state и logout вместо доступа к обычным функциям PubChat;
- снятие/истечение restriction не восстанавливает ранее отозванные sessions: Account проходит нормальную повторную аутентификацию;
- PostgreSQL integration и contract tests фиксируют platform-only scope, session revocation, active/revoke semantics, узкий HTTP exemption surface и HTTP/realtime enforcement hooks.

Следующий отдельный Trust & Safety task — hardening moderation hierarchy/permissions; AI-assessment остаётся последующим этапом после human authority path.

Quality gate: exact-head CI #524 green before merge.

## [0.6.10-alpha.1] — 2026-09-17

Stage 6.8 checkpoint 1 — production-grade Trust & Safety foundation.

- platform Trust & Safety intake отделён от Space-local moderation и принимает Persona, received Messenger message и Space message reports;
- server-owned priority, duplicate/rate guard, moderator queue claim/release и privacy-bounded evidence access фиксируют операционный report flow;
- evidence viewing и решения пишутся в append-only audit trail, а пользователь получает понятный public explanation;
- platform roles получили authority levels (`user=0`, `moderator=50`, `admin=100`), а санкции требуют одновременно permission и `actor_authority > target_authority`;
- добавлены durable Account-level capability restrictions с platform/Space scope, temporary/permanent duration, authority snapshots и revoke history;
- permanent restrictions и полный `account.access` требуют отдельных elevated permissions;
- server-side enforcement подключён для `messenger.send`, `space.chat.send`, `media.upload`, `space.create`, `space.join`, `invitation.send`, `profile.edit` и `discovery.publish`;
- restriction API не предлагает capabilities без реального backend enforcement;
- Safety Center показывает Account его ограничения, причину, scope и expiry;
- platform-restriction appeals имеют отдельную queue, claim/release, authority checks и independent-review preference; overturn revoke-ит restriction, не стирая историю;
- moderator Trust & Safety UI поддерживает report triage, evidence, restriction issue/revoke и appeal review;
- AI-copilot boundary зафиксирован документально: AI помогает triage/evidence/recommendation, но не имеет punitive authority в beta baseline.

`account.access` в этом checkpoint ещё намеренно не выдавался до появления полного session/HTTP/realtime enforcement; это закрыто в `0.6.11-alpha.1`.

Quality gate: exact-head CI → release sync → exact-head CI перед merge.

## [0.6.9-alpha.1] — 2026-09-16

Stage 6 checkpoint 10 — Web Push / PWA Messenger delivery.

- добавлена Account-owned per-device модель `web_push_subscriptions` с endpoint fingerprinting и lifecycle API для register/status/remove;
- Web Push остаётся явным opt-in: browser permission запрашивается только после действия пользователя и никогда не появляется при bootstrap приложения;
- VAPID private key хранится только на backend; клиент получает только public key и capability status;
- offline push queue создаётся только для Messenger и только когда получатель offline; Space chat по-прежнему не создаёт background push pressure;
- push payload privacy-minimal: без текста личного сообщения, sender identity и иных данных переписки; click destination ограничен same-origin Messenger route;
- перед network delivery повторно проверяются Redis presence, текущий opt-in, unread state и Account block/privacy;
- Web Push использует тот же durable `external_delivery_ledger`: per-conversation cooldown/dedupe, `FOR UPDATE SKIP LOCKED`, expiring claim lease и bounded retry/backoff;
- terminal provider responses `404/410` удаляют протухшие subscriptions; retryable failures остаются bounded;
- push worker вынесен в отдельные systemd oneshot/timer units и не живёт внутри Uvicorn lifecycle;
- logout/session teardown инвалидирует local PushSubscription, чтобы shared browser/device не продолжил получать уведомления предыдущего Account;
- service worker получил `push`/`notificationclick`, сохранив static-only cache contract: auth/API/private data по-прежнему не кэшируются;
- Notifications UI получил email/Web Push preference controls и explicit device opt-in flow;
- добавлены migration `k0a6d4f88006`, deterministic Web Push privacy/provider/endpoint tests и PWA regression guard;
- functional exact-head CI прошёл migration/schema/backend/PostgreSQL/Redis Sentinel/multiprocess/rolling-deploy/frontend gates перед release-doc sync.

Следующий launch-critical workstream — production-grade moderation / Trust & Safety end-to-end flow; параллельно продолжаются browser/security/observability gates и формализация unit economics/monetization boundaries.

Quality gate: functional exact-head CI → version/docs sync → повторный exact-head CI перед merge.

## [0.6.8-alpha.1] — 2026-09-16

Stage 6 checkpoint 9 — durable unread-Messenger email delivery.

- добавлен privacy-minimal `external_delivery_ledger`: durable status/retry/provider metadata, aggregate counts и dedupe keys без текста личных сообщений и без сохранения email destination в ledger;
- scheduled candidate worker выбирает только давно отсутствующие Account с unread Messenger, подтверждённым email и явным `email_unread_dm_nudge` opt-in;
- Redis presence проверяется до queue и непосредственно перед delivery; вернувшийся online Account не получает offline nudge и не расходует retry budget;
- Account block/privacy повторно проверяются перед queue/delivery, при этом legacy `PrivateMessage`/`RoomMember` UIDs явно сопоставляются через `Account.legacy_user_uid`;
- Account-level cooldown не обходится новым входящим DM: внешний re-engagement остаётся периодическим агрегированным напоминанием, а не письмом на каждое сообщение;
- SMTP adapter поддерживает STARTTLS/implicit SSL, privacy-safe plain/HTML template, stable RFC Message-ID и разделение retryable/terminal provider failures;
- delivery worker использует PostgreSQL `FOR UPDATE SKIP LOCKED`, expiring claim lease и bounded exponential backoff; stale opt-out/read/block state переводит запись в `suppressed`;
- worker claim-ит только непосредственно обрабатываемую запись, чтобы длинный SMTP batch не позволял lease более поздних записей истечь до отправки;
- добавлены CLI queue/deliver/all stages, отдельные systemd oneshot/timer и installer с security/realtime/SMTP preflight;
- PostgreSQL integration test проверяет disjoint concurrent claims и recovery expired lease;
- добавлен `docs/message-email-delivery-v1.md` с production/retry/privacy контрактом и явной оговоркой, что SMTP не даёт абсолютный exactly-once после crash-after-send;
- все существующие PostgreSQL/Redis Sentinel/recovery, multi-process WebSocket, rolling deploy и frontend gates остаются зелёными.

Следующий Stage 6.3 slice: standards-based Web Push/PWA delivery и notification permission/subscription UX; параллельно продолжаются browser/security/observability gates.

Quality gate: functional exact-head CI → version/docs sync → повторный exact-head CI перед merge.

## [0.6.7-alpha.1] — 2026-09-16

Stage 6 checkpoint 8 — message notification policy / active context baseline.

- добавлены account-level настройки Messenger/Space in-app уведомлений и звуков, а также opt-in flags для будущих email/Web Push adapters;
- Messenger active context хранится как connection-scoped TTL state в Redis и обновляется heartbeat/reconnect;
- Space active context использует уже существующий distributed room presence contract;
- server-side delivery policy подавляет дублирующий toast/sound, когда получатель уже смотрит тот же conversation/Space, не меняя authorization/message delivery;
- offline external re-engagement разрешён только для Messenger и только по opt-in; Space chat для offline Account не создаёт background notification pressure;
- Space alert fan-out ограничен active membership, online presence и Account block boundaries;
- SPA объединяет Messenger/Space message alerts и использует существующие `private_notification.mp3` / `chat_notification.mp3`;
- добавлена Alembic migration `k0a6d4f88004` и API для чтения/изменения message notification preferences;
- deterministic tests фиксируют online/offline/active-context policy и active-context lifecycle;
- Redis Sentinel/restart recovery, multi-process WebSocket, production rolling deploy, PostgreSQL migration/recovery и frontend gates остаются зелёными.

Durable email delivery ledger, scheduled unread-DM nudge worker, provider retry/backoff и Web Push остаются следующими Stage 6.3 slices.

Quality gate: functional CI → version/docs sync → повторный exact-head CI перед merge.

## [0.6.6-alpha.1] — 2026-09-16

Stage 6 pre-beta hardening checkpoint 7 — Redis Sentinel failover/capacity baseline.

- добавлен backward-compatible Redis topology layer: direct `REDIS_URL` и Redis Sentinel master discovery;
- Sentinel mode поддерживает отдельные master/Sentinel credentials, DB, timeout и peer-validation settings;
- `RealtimeService` больше не привязан к фиксированному master host и создаёт command/PubSub connections через failover-aware pool;
- production deploy preflight принимает direct или complete Sentinel configuration и отклоняет частично заданную topology config;
- CI поднимает реальный Redis master + replica + три Sentinel process с quorum `2`;
- текущий master реально останавливается, Sentinel promotes replica, а те же `RealtimeService` objects восстанавливают ticket issue/consume без restart application process;
- PubSub subscription автоматически пересоздаётся через promoted master и снова принимает события;
- bounded concurrent ticket bursts проверяются до и после promotion как correctness/capacity baseline без искусственных throughput-обещаний;
- restart recovery, multi-process WebSocket, rolling deploy, PostgreSQL migration/recovery и frontend gates остаются зелёными.

Redis остаётся ephemeral realtime слоем: failover не делает one-time tickets, presence или pub/sub durable. Durable message/history/membership state остаётся в PostgreSQL.

Следующий активный Stage 6 workstream: notification/message delivery hardening (online/offline policy, active-context suppression, unread-Messenger email nudge и Web Push), параллельно с observability/security/browser gates.

Quality gate: real Sentinel promotion CI → main sync → version/docs sync → повторный exact-head CI перед merge.

## [0.6.5-alpha.2] — 2026-09-16

Stage 6 parallel stabilization checkpoint — production deploy reliability + messaging UX polish.

- production backend переведён на Uvicorn multiprocess supervisor с минимум двумя workers при `DEBUG=False`;
- systemd владеет постоянным listener `127.0.0.1:9000` через `pubchat-backend.socket`, поэтому supervisor restart не создаёт connection-refused окно для nginx;
- routine deploy использует `SIGHUP` rolling worker reload вместо остановки единственного listener;
- добавлены `/health/live` и dependency-aware `/health/ready` для PostgreSQL + production Redis;
- tracked deploy script выполняет security/Redis preflight, migrations, staged frontend build, rolling reload и readiness gate;
- SPA build сначала собирается в `dist.next`, затем публикует static/hash assets и только после них `index.html`, не очищая live build во время сборки;
- CI реально проверяет inherited persistent socket, SIGHUP worker replacement и queued HTTP request во время полного supervisor replacement без connection-refused;
- authenticated SPA bootstrap повторяет transient network/`502`/`503`/`504` ошибки с bounded backoff;
- Space chat и Messenger получили compact messaging UX pass: attachment shelf, более плотный composer, calmer message chrome и responsive controls;
- desktop Space info panel больше не показывает overlay-only close control на широком layout.

Это patch checkpoint внутри `0.6.5`: следующий инфраструктурный Stage 6.2 checkpoint остаётся Redis failover topology/capacity.

Quality gate: production-deploy/realtime/frontend functional CI → version/docs sync → повторный exact-head CI перед merge.

## [0.6.5-alpha.1] — 2026-09-16

Stage 6 pre-beta hardening checkpoint 6 — bounded WebSocket backpressure.

- каждый process-local WebSocket имеет отдельную bounded outbound queue;
- Redis/pub-sub fan-out больше не ждёт socket write каждого клиента и только ставит frame в локальную очередь;
- один sender task на socket сохраняет порядок кадров;
- переполнение очереди изолированно отключает только медленного клиента с WebSocket code `1013`;
- socket send timeout также изолирует stalled consumer и не задерживает delivery другим соединениям;
- лимит очереди настраивается через `REALTIME_OUTBOUND_QUEUE_SIZE` (default `64`);
- deterministic tests проверяют порядок, non-blocking overflow и send-timeout isolation;
- все PostgreSQL/Redis recovery, multi-process rolling-restart и frontend gates остаются зелёными.

Остаётся Stage 6.2 задача: Redis failover topology/capacity tests. Общий load/capacity profiling продолжается также в performance/operations блоках Stage 6.

Quality gate: functional exact-head CI → version/docs sync → повторный exact-head CI перед merge.

## [0.6.4-alpha.1] — 2026-09-16

Stage 6 pre-beta hardening checkpoint 5 — real multi-process WebSocket / rolling-restart baseline.

- CI поднимает два отдельных Uvicorn/FastAPI process против общих PostgreSQL и Redis;
- one-time realtime ticket выдаётся вне worker process и consume-ится внутри конкретного WebSocket worker;
- distributed presence виден между процессами через Redis;
- Redis pub/sub доставляет user event в worker, который владеет process-local WebSocket object;
- один Uvicorn process останавливается как часть rolling restart, в то время как второй продолжает обслуживать realtime traffic;
- после запуска replacement process клиент подключается заново с новым one-time ticket и снова получает realtime события;
- существующие PostgreSQL migration/recovery, Redis restart/recovery и frontend gates продолжают проходить в том же pipeline;
- добавлен `docs/realtime-multiprocess-v1.md`.

Остаются Stage 6.2 задачи: slow-client/backpressure под нагрузкой и Redis failover topology/capacity tests.

Quality gate: functional exact-head CI → version/docs sync → повторный exact-head CI перед merge.

## [0.6.3-alpha.1] — 2026-09-16

Stage 6 pre-beta hardening checkpoint 4 — Redis restart/recovery.

- CI намеренно останавливает Redis 7.2 service container;
- при `DEBUG=False` outage обязан проявляться как `RealtimeUnavailable`, process-local fallback запрещён;
- Redis запускается снова в том же CI job;
- те же, уже созданные `RealtimeService` objects восстанавливают ticket issue/consume без restart Python process;
- pub/sub listener автоматически пересоздаёт subscription после Redis restart;
- cleanup гарантированно возвращает Redis в рабочее состояние даже при падении assertion;
- PostgreSQL migration/recovery и frontend gates продолжают проходить в том же pipeline;
- добавлен `docs/redis-recovery-v1.md`.

Ephemeral Redis keys (presence, unconsumed tickets, TTL counters, transient pub/sub) не превращаются в durable state: после outage протокол восстанавливает transport/reconnect там, где это нужно.

Остаются Stage 6.2 задачи: реальные multi-process WebSocket/Uvicorn scenarios, rolling-restart client reconnect, slow-consumer/backpressure/load и Redis failover topology.

Quality gate: functional exact-head CI → version/docs sync → повторный exact-head CI перед merge.

## [0.6.2-alpha.1] — 2026-09-16
Stage 6 checkpoint 3 — Redis 7.2 production-semantics baseline: distributed one-time tickets/TTL, presence, rate limits, idempotency и cross-instance protocol-v2 pub/sub при `DEBUG=False`.

## [0.6.1-alpha.1] — 2026-09-16
Stage 6 checkpoint 2 — PostgreSQL 16 backup/restore recovery drill: portable custom-format dump, restore в отдельную DB, Alembic head/zero drift и повторные semantic legacy assertions.

## [0.6.0-alpha.1] — 2026-09-16
Stage 6 checkpoint 1 — PostgreSQL 16 clean historical migration, `alembic check`, async integration, representative legacy-data rehearsal, DB URL hardening и explicit ORM registry для standalone processes.

## [0.5.5-alpha.1] — 2026-09-16
Stage 5.6 — installable PWA shell, static-only service-worker cache, external reminder worker с durable cursor и centralized notification lifecycle.

## [0.5.4-alpha.1] — 2026-09-15
Stage 5.5 — explainable organic Space discovery: eligibility-first ranking, server-only score, organic activity/context signals и no-paid/no-gift boundary.

## [0.5.3-alpha.1] — 2026-09-15
Stage 5.4 — consent-first internal gifts, append-only support ledger, cosmetic entitlements и Persona/Space support UI без real-money flows.

## [0.5.2-alpha.1] — 2026-09-15
Stage 5.3 — bounded Activity Occurrences, opt-in reminders, private notification inbox и idempotent reconciliation.

## [0.5.1-alpha.1] — 2026-09-15
Stage 5.2 — system-earned achievements и Activity Conversation Rounds без score/winner/prize/stake.

## [0.5.0-alpha.1] — 2026-09-15
Stage 5.1 — Persona/Space appearance, recurring Activities, RSVP и mobile-first product identity UI.

## [0.4.0-alpha.1] — 2026-09-15
Stage 4 — canonical Living Spaces, memberships/scoped roles, social graph, invitations, Rules/Events/History и transparent moderation/appeals.

## [0.3.0-alpha.1] — 2026-09-15
Stage 3 — Realtime v2: one-time WebSocket tickets, Redis pub/sub/presence, heartbeat/reconnect, rate limits/idempotency и memory-only browser access JWT.

## [0.2.0-alpha.1] — 2026-09-15
Stage 2 — Identity v2: Account/Persona/Credential/Session/Privacy, RBAC и Persona-first SPA shell.

## [0.1.0-alpha.1] — 2026-09-15
Stage 1 — revival foundation/security: server-side admin authorization, IDOR/mass-assignment fixes, secret/token logging hardening, DB health check и CI.

## [0.0.0-alpha.0] — legacy baseline
Исходное состояние старого проекта до revival. Историческая точка отсчёта, не рекомендуемый релиз.

Подробные технические контракты находятся в `docs/README.md`, `docs/roadmap.md` и профильных `docs/*`.