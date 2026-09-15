# PubChat — история версий

Формат до стабильного релиза: `MAJOR.MINOR.PATCH-channel.N`.

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
