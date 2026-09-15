# PubChat versioning policy

## Current release

`0.3.0-alpha.1`

The canonical value lives in the repository root `VERSION` file. `CHANGELOG.md` records released and in-development lines.

## Format

Before `1.0.0`, PubChat uses Semantic Versioning with an explicit readiness channel:

`0.MINOR.PATCH-alpha.N`
`0.MINOR.PATCH-beta.N`
`MAJOR.MINOR.PATCH` for stable releases.

Examples:
- `0.4.0-alpha.0` — an active development line, incomplete and allowed to change quickly;
- `0.4.0-alpha.3` — third validated alpha checkpoint in the same milestone;
- `0.9.0-beta.1` — core product flows complete and entering stabilization;
- `1.0.0` — first stable public release.

## Meaning of the numbers

While MAJOR is `0`:
- **MINOR** increases when a planned revival/product milestone becomes a coherent release line (foundation, identity, realtime, Living Spaces, etc.);
- **PATCH** increases for backward-compatible fixes or small additions inside the same milestone;
- **alpha.N / beta.N** is the readiness checkpoint for that exact numeric version.

After `1.0.0`, normal SemVer rules apply: MAJOR for incompatible public-contract changes, MINOR for compatible features, PATCH for compatible fixes.

## Readiness channels

### Alpha

Use alpha while one or more core product domains are incomplete. Schema/API contracts may still evolve, although data-preserving migrations are preferred. Alpha must still pass CI for any checkpoint we record as a released version.

PubChat is currently alpha because Living Spaces, the complete social graph, discovery/privacy policies, rules/events/history and the moderation/report/appeal product loop are not yet complete.

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
- automated regression coverage for the critical paths.

During beta, new architecture-level rewrites are avoided. Work focuses on correctness, performance, observability, accessibility and UX stabilization.

### Stable

Stable begins at `1.0.0` only after the beta launch gate is satisfied in a production-like environment and there are no known P0/P1 launch blockers. Public API/data compatibility becomes an explicit release commitment.

## Release workflow

1. Review actual merged changes and open blockers.
2. Confirm CI on the exact release head.
3. Update `VERSION` and `CHANGELOG.md` in the same release change.
4. Verify backend and frontend expose the same version.
5. Merge the release change to `main`.
6. Start the next milestone as `next-minor-alpha.0` in its development branch.

A version number is therefore a readiness statement, not a count of commits.

## Historical mapping

- `0.0.0-alpha.0` — legacy baseline before revival;
- `0.1.0-alpha.1` — security/foundation baseline;
- `0.2.0-alpha.1` — Identity v2 + SPA shell;
- `0.3.0-alpha.1` — Realtime v2 + resilient client transport;
- `0.4.0-alpha.0` — Living Spaces & social graph development line (unreleased).
