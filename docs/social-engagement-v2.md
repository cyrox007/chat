# PubChat Stage 5.2 — Earned Achievements & Conversation Rounds

Development line: `0.5.1-alpha.x`, based on released `0.5.0-alpha.1`.

## Goal

Strengthen reasons to return to PubChat without buying status or turning the product into a competitive/ азартный game. The second Stage 5 slice adds visible memories of participation and lightweight social play inside existing Space Activities.

## Earned Achievements

Achievements are cosmetic records of product participation. They are **not** reputation, trust, moderation authority, access control or discovery ranking signals.

Foundation:

- immutable achievement code/catalog;
- title, description, icon preset and category;
- account-level award record with `earned_at`;
- optional Space context;
- explicit system source (`activity_created`, `conversation_round_participated`, etc.);
- one account can earn a given achievement code once unless a later design explicitly introduces repeatable collectibles.

Initial system-earned achievements:

- `first_host` — created the first Space Activity;
- `conversation_starter` — opened the first Conversation Round;
- `first_round_response` — participated in a Conversation Round for the first time.

These are intentionally easy, descriptive onboarding milestones. They do not rank users and cannot be granted by payment.

## Conversation Rounds

A Conversation Round is a small social interaction attached to a Space Activity. It is designed to create a reason to talk, not to produce winners.

Initial round types:

- `icebreaker` — one prompt, each participant can leave one short response;
- `choice` — prompt + two short choices, participant selects one and may add a short comment;
- `story_chain` — one prompt, participants add one short continuation each.

Not in this slice:

- scores;
- wagering/stakes;
- randomized paid rewards;
- loot boxes;
- cash/value prizes;
- competitive ladders;
- purchasable achievement progress;
- anonymous responses that bypass Account-level block/moderation rules.

## Permissions and privacy

- Activity creator or scoped Space owner/moderator can open/close a round;
- only active Space members can respond;
- responses are account-bound and use Persona projection for display;
- one response per account for `icebreaker` and `choice`;
- `story_chain` can allow multiple turns only through an explicit bounded limit in a later iteration; first slice uses one response per account for all round types;
- closed/cancelled Activity cannot accept new rounds or responses;
- block/trust rules remain Account-level and are not weakened by games.

## Data model

- `achievement_definitions` — catalog seeded by additive migration;
- `account_achievements` — unique `(account_uid, achievement_code)` award;
- `conversation_rounds` — Activity-scoped prompt and lifecycle;
- `conversation_round_responses` — unique `(round_uid, account_uid)` response.

The models contain no permission/rating/reputation fields.

## API

Planned versioned contracts:

- `GET /achievements/v1/me`
- `GET /achievements/v1/accounts/{account_uid}` — respects profile privacy/block policy;
- `GET /activities/v1/{activity_uid}/rounds`
- `POST /activities/v1/{activity_uid}/rounds`
- `PATCH /activities/v1/{activity_uid}/rounds/{round_uid}`
- `GET /activities/v1/rounds/{round_uid}/responses`
- `PUT /activities/v1/rounds/{round_uid}/response`

No endpoint allows a client to grant itself an achievement.

## UI / UX

- Achievement shelf on Persona profile;
- “Мои достижения” view for the full private history;
- Conversation Round card inside “Жизнь пространства”;
- prompt, current responses/choice split and one clear participation action;
- mobile-first, no leaderboard-first layout.

## Release gate

- additive migration with one Alembic head;
- typed allowlisted schemas;
- system-only achievement grant service;
- server-side Space membership/manager checks;
- profile privacy for public achievement shelf;
- no privileged fields in writable DTO;
- backend contract tests;
- production SPA build;
- final self-review for abuse/spam/privacy;
- canonical version bump only after a green functional exact-head CI;
- second exact-head CI on the final release number before merge.
