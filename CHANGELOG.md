# PubChat — история версий

Формат до стабильного релиза: `MAJOR.MINOR.PATCH-channel.N`.

## [0.6.7-alpha.1] — 2026-09-16

Stage 6 checkpoint 8 — message notification policy / active-context baseline.

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
