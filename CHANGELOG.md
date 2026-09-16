# PubChat — история версий

Формат до стабильного релиза: `MAJOR.MINOR.PATCH-channel.N`.

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

- CI намеренно останавливает реальный Redis 7.2 service container;
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