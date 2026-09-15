# PubChat — история версий

Формат до стабильного релиза: `MAJOR.MINOR.PATCH-channel.N`.

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
