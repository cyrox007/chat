# PubChat Identity v2

## Why it exists

Legacy `users` mixes authentication, public profile, platform role, rating, privacy-adjacent fields and social data in one row. Identity v2 separates those responsibilities so PubChat can support Persona, privacy, multiple clients and later multiple Personas without making security depend on public profile data.

## Canonical entities

### Account

Private platform identity and lifecycle. Account is the subject of authentication, trust, abuse controls, blocks and platform roles.

Account is not a public profile.

### Persona

Public social identity: handle, display name, avatar, bio and social intent. A primary Persona exists today; the schema allows multiple Personas later without pretending they are independent Accounts.

### Credential

Authentication/recovery material such as password, email and phone. Credential data does not belong in public Persona responses.

### IdentitySession

Server-side refresh session. Only SHA-256 of the high-entropy refresh token is stored in the canonical session table. Sessions can be rotated and revoked independently.

### PrivacySettings

Persona-facing privacy and contact preferences. Location is hidden by default. DM policy is exposed to clients as social/contact context; full server-side messaging enforcement belongs to the social/messaging workstream.

### PlatformRole / PlatformPermission

Platform authorization is separate from Persona reputation and, later, Space-scoped roles. Admin API authorization reads Identity v2 RBAC instead of trusting frontend state or JWT role claims.

### AccountRelationship

Account-level relationship foundation for block/friend/follow-style semantics. A future Persona cannot bypass an Account-level block.

## API projections

`/identity/v2` is the client-facing identity surface.

- `POST /register` — creates Account + primary Persona + password Credential + PrivacySettings + Session and signs the client in;
- `POST /login` — authenticates handle/email/legacy phone + password;
- `POST /refresh` — rotates the refresh session;
- `POST /logout` — revokes the current refresh session;
- `GET /me` — private authenticated Account/Persona projection;
- `GET /profiles/{account_uid}` — privacy-aware social profile;
- `POST /personas/batch` — minimal presence projection for shared realtime UI;
- `PATCH /persona` — edit the current primary Persona;
- `PATCH /privacy` — edit current Persona privacy/contact settings.

ORM objects are never intended to be public API contracts.

## Migration strategy

The migration is deliberately additive.

1. New tables are created next to legacy `users`.
2. Every existing user is backfilled into one Account and one primary Persona.
3. Existing password/email/phone material is moved into Credential rows.
4. Legacy global roles are mapped to platform RBAC.
5. Existing refresh cookies are lazily upgraded to `IdentitySession` on first v2 refresh, avoiding a forced logout wave.
6. New SPA registration writes Identity v2 and a minimal legacy User row while rooms/messages still reference `users.uid`.
7. Feature-by-feature migration removes legacy reads. Sensitive `/users/{uid}` and `/users/by-uids` reads are already retired.
8. Legacy `users` security/profile columns can be removed only after rooms, messages, moderation and admin stop depending on them.

## Compatibility rules

- New frontend/native features must not add fields to legacy `users` API contracts.
- New public identity reads use Persona projections.
- New authorization reads Account/RBAC or later Space-scoped permissions.
- Compatibility writes may synchronize the small subset still consumed by old room/messenger code, but Identity v2 remains canonical.

## Known transitional debt

- browser access token is still persisted in `localStorage`; refresh token is HttpOnly and server-side sessions store only its hash;
- the old `/users/registration`, `/users/login` and related routes remain deprecated for old clients;
- rooms/messages still reference legacy `users.uid`;
- DM policy is represented in Identity v2 but hard enforcement will be integrated with messaging/social rules;
- only the primary Persona is active in the UI; multi-Persona switching is a later product stage.

These are explicit migration constraints, not target architecture.
