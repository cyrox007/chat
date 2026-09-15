# PubChat versioning policy

## Current release

`0.5.0-alpha.1`

Active development line: `0.5.1-alpha.0`.

The canonical released value lives in the repository root `VERSION` file. `CHANGELOG.md` records released and in-development lines.

## Format

Before `1.0.0`, PubChat uses Semantic Versioning with an explicit readiness channel:

`0.MINOR.PATCH-alpha.N`
`0.MINOR.PATCH-beta.N`
`MAJOR.MINOR.PATCH` for stable releases.

Examples:
- `0.5.1-alpha.0` — active compatible development inside the Stage 5 milestone;
- `0.5.1-alpha.1` — first validated checkpoint of that patch line;
- `0.9.0-beta.1` — core product flows complete and entering stabilization;
- `1.0.0` — first stable public release.

## Meaning of the numbers

While MAJOR is `0`:
- **MINOR** increases when a planned revival/product milestone becomes a coherent release line (foundation, identity, realtime, Living Spaces, product identity, etc.);
- **PATCH** increases for backward-compatible feature slices or fixes inside the same milestone;
- **alpha.N / beta.N** is the readiness checkpoint for that exact numeric version.

After `1.0.0`, normal SemVer rules apply: MAJOR for incompatible public-contract changes, MINOR for compatible features, PATCH for compatible fixes.

## Readiness channels

### Alpha

Use alpha while one or more launch-critical product/hardening domains are incomplete. Schema/API contracts may still evolve, although data-preserving migrations are preferred. Every recorded alpha checkpoint must pass CI on the exact release head.

PubChat remains alpha even though Identity, Realtime, Living Spaces, social graph, moderation and the first product-identity slice are implemented. Pre-beta hardening is still incomplete: production-like PostgreSQL/Redis integration coverage, migration rehearsal, observability, accessibility, load testing, legacy compatibility reduction and final security review remain required.

### Beta

Beta starts only after all launch-critical user journeys work end-to-end:
- registration/login/session recovery;
- Persona/profile/privacy;
- Space discovery/create/join/leave and scoped roles;
- realtime rooms and direct messages;
- friend/follow/block relationship model;
- reports, moderation actions and appeal trail;
- production migrations and multi-worker Redis operation;
- responsive mobile/desktop UX;
- automated regression coverage for critical paths;
- production-like integration/load/observability gate.

During beta, new architecture-level rewrites are avoided. Work focuses on correctness, performance, observability, accessibility and UX stabilization.

### Stable

Stable begins at `1.0.0` only after the beta launch gate is satisfied in a production-like environment and there are no known P0/P1 launch blockers. Public API/data compatibility becomes an explicit release commitment.

## Release workflow

1. Review actual merged changes and open blockers.
2. Confirm functional CI on the exact candidate head.
3. Update `VERSION` and convert the matching `CHANGELOG.md` Unreleased section into a release entry.
4. Verify backend and frontend expose the same version.
5. Run CI again on the exact versioned head.
6. Merge only after that second gate succeeds.
7. Start the next compatible slice as a new patch `alpha.0`, or the next milestone as a new minor `alpha.0`.

A version number is therefore a readiness statement, not a count of commits.

## Historical mapping

- `0.0.0-alpha.0` — legacy baseline before revival;
- `0.1.0-alpha.1` — security/foundation baseline;
- `0.2.0-alpha.1` — Identity v2 + SPA shell;
- `0.3.0-alpha.1` — Realtime v2 + resilient client transport;
- `0.4.0-alpha.1` — Living Spaces, social graph and transparent moderation;
- `0.5.0-alpha.1` — Persona/Space appearance + recurring Activities;
- `0.5.1-alpha.0` — earned achievements and Conversation Rounds development line.
