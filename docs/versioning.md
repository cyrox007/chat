# PubChat versioning policy

## Current release

`0.5.5-alpha.1`

Next development line: `0.6.0-alpha.0` — Pre-beta hardening.

The canonical released value lives in the repository root `VERSION` file. `CHANGELOG.md` records released checkpoints; active work is additionally tracked in `docs/roadmap.md` and domain documents.

## Format

Before `1.0.0`, PubChat uses Semantic Versioning with an explicit readiness channel:

`0.MINOR.PATCH-alpha.N`
`0.MINOR.PATCH-beta.N`
`MAJOR.MINOR.PATCH` for stable releases.

Examples:
- `0.6.0-alpha.0` — active development of the next milestone;
- `0.6.0-alpha.1` — first validated checkpoint of that milestone;
- `0.9.0-beta.1` — core product flows complete and entering stabilization;
- `1.0.0` — first stable public release.

## Meaning of the numbers

While MAJOR is `0`:
- **MINOR** increases when a planned product milestone becomes a coherent release line;
- **PATCH** increases for backward-compatible feature slices/fixes inside the milestone;
- **alpha.N / beta.N** is the readiness checkpoint for that exact numeric version.

After `1.0.0`, normal SemVer rules apply.

## Alpha

Alpha is used while launch-critical hardening or product domains are incomplete. Schema/API contracts may still evolve, although data-preserving migrations are preferred. Every recorded alpha checkpoint must pass CI on the exact versioned head.

PubChat remains alpha because production-like PostgreSQL/Redis integration coverage, migration rehearsal, observability, accessibility, load testing, legacy compatibility reduction and final security review are still required.

## Beta

Beta starts only after launch-critical user journeys work end-to-end and production-like integration/load/observability gates pass. During beta, architecture-level rewrites are avoided; work focuses on correctness, performance, accessibility and stabilization.

## Stable

Stable begins at `1.0.0` only after beta launch gate and absence of known P0/P1 launch blockers. Public API/data compatibility becomes an explicit commitment.

## Release workflow

1. Review actual feature scope and blockers.
2. Freeze candidate head.
3. Run functional CI on that exact head.
4. Update `VERSION` and release documentation only after success.
5. Run CI again on the exact versioned head.
6. Merge only after the second gate succeeds.
7. Start the next compatible slice as next patch `alpha.0`, or next milestone as next minor `alpha.0`.

Version number is a readiness statement, not commit count.

## Historical mapping

- `0.0.0-alpha.0` — legacy baseline;
- `0.1.0-alpha.1` — foundation/security;
- `0.2.0-alpha.1` — Identity v2 + SPA shell;
- `0.3.0-alpha.1` — Realtime v2;
- `0.4.0-alpha.1` — Living Spaces/social/moderation;
- `0.5.0-alpha.1` — Persona/Space appearance + recurring Activities;
- `0.5.1-alpha.1` — earned achievements + Conversation Rounds;
- `0.5.2-alpha.1` — Activity Occurrences + private in-app reminders/inbox;
- `0.5.3-alpha.1` — consent-first internal gifts + cosmetic support ledger/entitlements;
- `0.5.4-alpha.1` — explainable organic Space discovery;
- `0.5.5-alpha.1` — installable PWA shell + external reminder worker + centralized notification lifecycle;
- `0.6.0-alpha.0` — next Pre-beta hardening development line.
