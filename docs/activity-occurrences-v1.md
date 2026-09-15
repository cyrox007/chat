# PubChat Stage 5.3 — Activity Occurrences & Notifications

Development line after `0.5.1-alpha.1`: `0.5.2-alpha.x`.

## Why this slice exists

Recurring `SpaceActivity` is intentionally a compact template. `next_starts_at` is useful for display, but reminders, attendance and future native push need a concrete occurrence identity.

PubChat therefore adds a bounded occurrence layer instead of expanding recurring activities forever.

## ActivityOccurrence

`ActivityOccurrence` is a concrete scheduled instance of an Activity template.

Rules:
- unique by `(activity_uid, starts_at)`;
- generated only inside a bounded rolling horizon;
- cancelled Activity does not generate new occurrences;
- deleting Activity cascades occurrences;
- occurrence identity is stable once materialized;
- recurrence template remains canonical and unchanged.

Initial materialization horizon: 45 days. The service may materialize fewer rows when enough occurrences are already available.

## Reminder preference

A member may opt into reminders for an Activity series.

Initial lead times are allowlisted:
- 15 minutes;
- 60 minutes;
- 1 day.

A reminder preference is personal Account state. It is not visible to Space managers or other members and does not affect discovery, reputation or RSVP counts.

## Notification inbox

`UserNotification` is a private Account-owned inbox entry.

Initial Stage 5.3 notification kind:
- `activity_reminder`.

Properties:
- idempotent dedupe key;
- title/body snapshot for stable history;
- optional Space/Activity/Occurrence context for navigation;
- read/unread state;
- no cross-account read API.

The first SPA implementation calls the same server-side reconciliation service on app bootstrap / inbox refresh. A future worker or native push scheduler can call the same service; notification business rules must not live in Vue.

This means `0.5.2` provides reliable in-app reminders while the user is active/returns to PubChat. Background OS push is explicitly a later delivery adapter, not faked by the SPA.

## Reminder reconciliation

For each enabled reminder preference:
1. materialize a bounded occurrence window;
2. find occurrences whose reminder time has passed but whose meeting has not become stale;
3. insert notification with DB-level dedupe;
4. never duplicate the same occurrence + lead-time reminder.

A small grace window after occurrence start allows an app returning near start time to surface the reminder. Very old occurrences do not create delayed spam.

## Invariants

- recurring template remains canonical;
- bounded occurrence rows only;
- Account reminder preferences are private;
- notification ownership is server-authoritative;
- notification links never bypass Space membership/visibility checks;
- no engagement score/streak/pressure mechanics;
- reminders are opt-in;
- backend API remains reusable for future Android/iOS clients.

## First UI

- reminder control inside Space Activity;
- personal notification inbox;
- unread indicator in app shell;
- clear loading/empty/error/read states;
- mobile-first layout;
- no browser permission prompt in this slice.

## Release gate

Before `0.5.2-alpha.1`:
- additive migrations only;
- one Alembic head;
- occurrence materialization/dedupe contracts;
- reminder ownership/privacy contracts;
- notification ownership/read contracts;
- production SPA build;
- final time-zone, privacy and notification-spam self-review;
- version bump only after green functional exact-head CI;
- second exact-head CI on the versioned release head.
