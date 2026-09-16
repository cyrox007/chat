# PubChat — история версий

Формат до стабильного релиза: `MAJOR.MINOR.PATCH-channel.N`.

## [0.6.2-alpha.1] — 2026-09-16

Stage 6 — Pre-beta hardening, checkpoint 3: Redis realtime production-semantics baseline.

### Redis integration
- backend CI поднимает реальный Redis 7.2 service вместе с PostgreSQL 16;
- dedicated realtime integration test выполняется с `DEBUG=False`, process-local fallback исключён;
- два независимых `RealtimeService` instance используют общий Redis state;
- one-time ticket создаётся одним instance, consume-ится другим и не принимается повторно;
- Redis TTL удаляет истёкший ticket;
- presence register/query/unregister работает cross-instance;
- rate-limit counter общий для нескольких workers;
- idempotency claim/release общий для нескольких workers;
- Redis pub/sub доставляет protocol-v2 event между независимыми service instances.

### Boundaries
- production realtime не должен молча переходить в process-local fallback;
- Redis остаётся ephemeral/distributed state, durable social/domain data остаются в PostgreSQL;
- restart/failure recovery, multi-process WebSocket tests, rolling-restart reconnect и load/backpressure остаются следующими Stage 6.2 slices.

Добавлен `docs/redis-realtime-integration-v1.md`.

Quality gate: functional exact-head CI с Redis 7.2 + PostgreSQL 16/recovery gates → version/docs sync → повторный exact-head CI перед merge.

## [0.6.1-alpha.1] — 2026-09-16

Stage 6 — Pre-beta hardening, checkpoint 2: PostgreSQL backup/restore recovery drill.

### Recovery contract
- fully migrated synthetic legacy rehearsal database выгружается PostgreSQL 16 `pg_dump` в custom format;
- backup создаётся с `--no-owner --no-privileges` для переносимого restore без исходных owner/ACL;
- dump обязан быть непустым;
- restore выполняется в отдельную пустую `chat_restore_ci`, а не поверх source database;
- PostgreSQL 16 `pg_restore` восстанавливает schema, Alembic revision и данные;
- restored DB повторно проходит `alembic current` и `alembic check`;
- те же semantic legacy assertions повторно проверяют Account/Persona/Credential/role backfill, Space settings/memberships/tags и active legacy-ban behavior уже после restore.

### Documentation / boundaries
- добавлен `docs/database-recovery-v1.md`;
- backup считается проверенным только после успешного restore + semantic data assertions;
- synthetic recovery drill не подменяет rehearsal на anonymized production-like snapshot;
- retention, encryption, off-site storage, RPO/RTO и media/object-storage recovery остаются pre-beta/production задачами.

Stage 6.1 всё ещё не завершён: остаются production-like snapshot rehearsal, member-capacity concurrency hardening и IANA/DST-correct recurring wall-clock semantics.

Quality gate: functional exact-head CI с PostgreSQL 16 dump/restore drill → version/docs sync → повторный exact-head CI перед merge.

## [0.6.0-alpha.1] — 2026-09-16

Stage 6 — Pre-beta hardening, checkpoint 1: PostgreSQL migration/integration baseline.

### PostgreSQL / migrations
- backend CI поднимает реальный PostgreSQL 16 service;
- clean-database `alembic upgrade head` проходит через всю historical migration chain;
- `alembic current` подтверждает единственную current head;
- `alembic check` закрепляет отсутствие model/schema drift;
- отдельная synthetic representative pre-revival DB проходит upgrade `4f3d66790cd3 -> head` с semantic data assertions;
- legacy fixture проверяет Account/Persona/Credential/role backfill, Space settings/memberships/tags и active legacy ban semantics;
- historical Identity v2 credential backfill исправлен через raw driver SQL без изменения salts/deterministic UUID formula;
- ORM metadata reconciled с уже выпущенной schema для Persona handle, refresh-token hash и Activity RSVP uniqueness;
- DB URL строится через SQLAlchemy `URL.create()`, поэтому credentials со спецсимволами корректно кодируются.

### Standalone process / worker integration
- добавлен единый ORM model registry bootstrap для non-web processes;
- standalone reminder worker больше не зависит от случайных import side effects FastAPI composition root;
- real async PostgreSQL smoke проверяет migrated core tables, durable `NotificationWorkerState` и row lock worker cursor;
- backend contract tests выполняются после migration rehearsal на той же CI базе.

### Documentation / release gates
- добавлен `docs/prebeta-hardening-v1.md`;
- development/release checklist требуют real PostgreSQL migration/schema-drift gates для DB-sensitive slices;
- roadmap отдельно показывает доказанные пункты и оставшийся Stage 6.1 scope.

Известные ограничения: synthetic fixture не заменяет rehearsal на anonymized production-like snapshot. Backup/restore drill, member-capacity concurrency hardening и IANA/DST recurrence остаются активными задачами Stage 6.1.

Quality gate: functional exact-head backend/frontend CI с PostgreSQL 16 и legacy-data rehearsal → version/docs sync → повторный exact-head CI перед merge.

## [0.5.5-alpha.1] — 2026-09-16

Stage 5.6 — Web Application Maturity.

### PWA / offline shell
- локальный installable manifest с существующими 192/512 icons;
- production-only service-worker registration;
- network-first navigation shell;
- runtime cache только для same-origin static assets;
- API/auth/realtime/fetch-XHR responses намеренно не кэшируются;
- access JWT/refresh state не попадают в service-worker cache;
- спокойный install prompt и update notice;
- accessibility: named install region, polite update live region, keyboard-visible dismiss focus;
- CI `check:pwa` guard закрепляет cache/privacy boundary.

### Reminder delivery foundation
- отдельный `python -m workers.notification_reconciler`;
- worker не запускается внутри FastAPI/Uvicorn lifecycle;
- bounded batch/max-batches;
- durable `NotificationWorkerState` cursor;
- `FOR UPDATE SKIP LOCKED` не позволяет overlap-run выполнять тот же sweep одновременно;
- cursor продолжает обработку между scheduler runs и сбрасывается после конца eligible Account set;
- crash/retry безопасен благодаря existing notification DB dedupe;
- additive Alembic migration сохраняет одну migration head.

### SPA lifecycle
- notification unread/sync/polling вынесен из Header в Vuex `notifications` module;
- `App.vue` владеет authenticated start/stop lifecycle и online reconciliation;
- Header стал presentation-only для notification badge;
- NotificationsView обновляет общий unread state после read/read-all;
- authenticated bootstrap защищён shared in-flight promise от двойного connect/sync;
- CI `check:lifecycle` guard закрепляет ownership границы.

### Documentation / operations
- добавлены `web-application-maturity-v1.md` и `ui-ux-pwa.md`;
- operations описывает внешний scheduler, cursor/lock semantics и PWA cache contract;
- system requirements фиксируют secure-context/HTTPS требования PWA;
- architecture обновлена PWA/browser-cache и external-worker boundaries.

Stage 5.6 не добавляет browser/native push и не обещает offline messaging/private data synchronization.

Quality gate: functional exact-head backend/frontend CI → version/docs sync → повторный exact-head CI перед merge.

## [0.5.4-alpha.1] — 2026-09-15

Stage 5.5 — Explainable Organic Discovery.

- новый `/discovery/v1/spaces`, отдельно от стабильного `/spaces/v1` catalog;
- eligibility/privacy/block policy применяется до ranking;
- activity signal считается по distinct recent authors, а не raw message volume;
- учитываются nearest allowed Activity/Event, shared topics/purpose, explicit social intent и modest freshness/member-count context;
- private/unlisted Space без active membership не раскрывает внутренний upcoming context;
- server-only ranking score не входит в public API;
- до трёх объяснимых причин «Почему здесь»;
- bounded candidate pool до 200 Spaces;
- diversity pass уменьшает однообразие purpose без обхода filters/privacy;
- legacy `Room.rating`, gifts/support, price/currency/payment не участвуют в ranking;
- SPA Space Discovery переведён на новый endpoint и показывает reasons + ближайший допустимый upcoming item;
- добавлены `discovery-v1.md` и `ui-ux-discovery.md`.

Известное alpha-ограничение: organic-v1 начинает bounded pool с canonical catalog, отсортированного по новизне. Очень старый Space вне первых 200 кандидатов может не попасть в ranking даже после новой активности. До beta candidate generation будет собираться из нескольких bounded источников без unbounded scan.

Quality gate: functional exact-head backend/frontend CI → version/docs sync → повторный exact-head CI перед merge.

## [0.5.3-alpha.1] — 2026-09-15

Stage 5.4 — Creator Support & Cosmetic Gifts.

### Support domain
- opt-in Persona support и Space support settings;
- allowlisted cosmetic gift catalog без price/currency;
- append-only support ledger с sender/target snapshot labels;
- cosmetic entitlements отделены от trust/permissions/reputation;
- Persona gifts подчиняются profile privacy + Account-level block;
- Space gifts требуют active membership;
- self-gift Persona и owner→own-Space gift запрещены;
- максимум 20 внутренних gifts с Account за rolling 24h;
- anti-spam count защищён Account row lock от concurrent bypass;
- public shelf показывает только gift + aggregate count;
- sender/message остаются private recipient/manager history;
- historical ledger сохраняется после удаления live target через `SET NULL` references + snapshots.

### SPA / UX
- support opt-in и private received history в «Стиле образа»;
- Persona support shelf + calm gift picker в profile;
- отдельный `/spaces/:uid/support`;
- Space shelf/gift flow;
- owner/moderator settings и private received history;
- contextual desktop/app-menu navigation без отдельного mobile bottom-nav item;
- no donor leaderboard, streak, urgency, wallet или currency UI.

### Product/security boundaries
- `/support/v1` typed contract;
- writable DTO не содержит price/amount/currency/balance/score/rank/trust/role/payment fields;
- support ledger не имеет public PATCH/DELETE API;
- gift count не влияет на moderation, trust, permissions или discovery ranking;
- реальные checkout/payment provider/payout/refund/chargeback flows отсутствуют и требуют отдельного financial/security review.

Quality gate: functional exact-head backend/frontend CI → version/docs sync → второй exact-head CI → squash merge.

## [0.5.2-alpha.1] — 2026-09-15

Stage 5.3 — Activity Occurrences & Notifications.

- bounded `ActivityOccurrence` с горизонтом 45 дней и unique Activity+start;
- recurring calendar regression без накопительного monthly drift;
- side-effect-free occurrence GET и отдельный explicit materialization command;
- opt-in reminders: 15 минут, 1 час, 1 день;
- максимум 200 активных Activity reminders на Account;
- private Account-owned notification inbox;
- DB-level dedupe: максимум одно reminder notification на occurrence;
- idempotent reconciliation/sync для SPA и будущего worker/native push adapter;
- `/activity-occurrences/v1` и `/notifications/v1`;
- reminder controls в Space Life без HTTP N+1;
- `/notifications` screen, unread/read/read-all и app-shell bell;
- periodic in-app sync без browser permission prompts;
- системная документация полностью реструктурирована: README, установка, требования, функции, архитектура, API/realtime, security/privacy, operations, troubleshooting, roadmap и UI notification contract.

Известное alpha-ограничение: recurrence пока UTC-anchored и не хранит IANA timezone; DST-correct wall-clock semantics входят в pre-beta hardening. Browser/native push в этот checkpoint не входит.

Quality gate: functional exact-head backend/frontend CI → version bump → повторный exact-head CI перед merge.

## [0.5.1-alpha.1] — 2026-09-15

Stage 5.2 — Earned Achievements & Conversation Rounds.

- system-only achievements и read-only `/achievements/v1`;
- public shelf + private own history без утечки source/context;
- `first_host`, `conversation_starter`, `first_round_response`;
- Activity-scoped `icebreaker`, `choice`, `story_chain`;
- один open round на Activity и один response на Account+round;
- Account-level block фильтрует ответы в обе стороны;
- score/rank/winner/prize/stake/currency отсутствуют;
- cancellation Activity закрывает open round;
- profile/activity SPA UI и mobile-first presentation.

## [0.5.0-alpha.1] — 2026-09-15

Stage 5.1 — Product Identity & Activities.

- Persona Appearance и privacy-aware public projection;
- Space Appearance и batch projection без N+1;
- cosmetics не влияют на trust/permissions/discovery ranking;
- recurring Activities `none/daily/weekly/monthly`;
- explicit timezone input, UTC API timestamps, `next_starts_at`;
- RSVP `interested/going`;
- экран «Стиль образа» и «Жизнь пространства».

## [0.4.0-alpha.1] — 2026-09-15

Stage 4 — Living Spaces & Social Core.

- `/spaces/v1`, canonical membership lifecycle и scoped roles;
- public/unlisted/private Spaces, open/request/invite flows;
- social graph: follow/friend/block;
- privacy-aware People discovery;
- account-bound Space invitations;
- Rules, Events, append-only History;
- Safety Center;
- reports/actions/appeals и manager moderation queue;
- scoped restrict синхронизирован с compatibility `RoomBan`;
- Space/People/Safety mobile-first SPA surfaces.

## [0.3.0-alpha.1] — 2026-09-15

Stage 3 — Realtime v2.

- one-time scoped WebSocket tickets вместо JWT в URL;
- Redis pub/sub, distributed presence и multi-worker delivery;
- heartbeat, reconnect/resume, rate limiting и server-side idempotency;
- slow-consumer timeout/backpressure;
- browser access JWT хранится только в памяти SPA;
- DM privacy/block policy применяется server-side.

## [0.2.0-alpha.1] — 2026-09-15

Stage 2 — Identity v2 & SPA shell.

- `Account != Persona`;
- Credential, IdentitySession, PrivacySettings, relationships, platform RBAC;
- additive legacy-user backfill;
- hashed refresh-token sessions;
- `/identity/v2` API;
- Persona-first onboarding/profile;
- mobile-first SPA shell и design tokens.

## [0.1.0-alpha.1] — 2026-09-15

Stage 1 — Foundation & Security.

- новая концепция PubChat и revival roadmap;
- server-side admin authorization;
- profile IDOR/mass-assignment fixes;
- sensitive legacy projection hardening;
- production-capable default secrets удалены;
- token logging удалён;
- DB health-check исправлен;
- GitHub Actions CI введён.

## [0.0.0-alpha.0] — legacy baseline

Исходное состояние старого проекта до revival. Историческая точка отсчёта, не рекомендуемый релиз.

Подробные доменные изменения и активный план находятся в `docs/README.md`, `docs/roadmap.md` и профильных документах `docs/*`.
