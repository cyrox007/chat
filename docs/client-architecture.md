# PubChat Client Architecture

## Current product shape

PubChat is a client-server application. The current primary client is a Vue 3 SPA built with Vite. It must behave like an application, not like a collection of independently reloaded web pages.

The SPA is the first client, not the definition of the backend contract. Native Android and iOS clients may be added later and should reuse the same domain model and public API semantics.

## Boundaries

### Backend owns

- Account identity and lifecycle;
- Persona and privacy rules;
- sessions and authentication;
- permissions and moderation decisions;
- Space membership and scoped roles;
- messaging rules and persistence;
- trust, anti-abuse and rate limits;
- authoritative realtime events.

A client must not be trusted to enforce authorization or privacy by itself.

### Client owns

- navigation and app shell;
- optimistic UI where the server contract permits it;
- responsive layout;
- local presentation state;
- accessibility and interaction patterns;
- reconnect/offline presentation;
- platform-specific capabilities such as push, camera or share sheets.

## SPA rules

- normal navigation uses Vue Router and must not reload the document;
- auth expiry returns the user to login through SPA state, not `window.location.href`;
- one application shell owns connection state, notifications and navigation;
- mobile is a first-class layout, with persistent bottom navigation where useful;
- server errors should degrade the affected feature instead of resetting the whole application;
- a 403 means “not allowed”, not “log the user out”;
- API responses must use stable projections instead of serializing ORM objects.

## API-first rule

New client-facing work targets versioned domain endpoints such as `/identity/v2`. Legacy `/users/*` routes are compatibility surfaces and must not receive new product features.

Public API projections are intentionally different by context:

- **Account projection** — private authenticated state;
- **Persona profile projection** — privacy-aware public/social state;
- **Persona presence projection** — minimal identity visible while sharing a realtime context;
- **admin/moderation projection** — privileged data only after server-side permission checks.

This separation must remain valid for web, Android and iOS clients.

## Authentication direction

Today the SPA uses:

- short-lived JWT access token;
- rotating refresh token in an HttpOnly cookie;
- server-side `IdentitySession` with only a hash of the refresh token;
- automatic refresh without page reload;
- lazy migration of legacy refresh sessions.

Access-token storage in `localStorage` remains transitional technical debt. Realtime v2 and later client-hardening work may move browser access-token state to memory and introduce platform-specific secure storage for native clients.

## Future native clients

Native Android/iOS are explicitly possible, but not a Stage 2 requirement. When added:

- business rules stay on the backend;
- API DTOs remain reusable;
- native secure storage replaces browser storage details;
- push notification tokens become device/session capabilities;
- camera, media picker, deep links and share sheets are adapters around the same domain actions;
- native navigation may differ visually without changing Account/Persona/Space semantics.

Do not introduce browser-only assumptions into domain models merely because Vue SPA is the current client.
