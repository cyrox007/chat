# PubChat Stage 5.3 — Activity Occurrences & Notifications

Released checkpoint: `0.5.2-alpha.1`.

## Зачем нужен этот slice

Recurring `SpaceActivity` остаётся компактным шаблоном. `next_starts_at` достаточно для простого отображения, но reminders и будущий push требуют стабильной identity конкретной встречи.

Поэтому PubChat добавляет bounded occurrence layer вместо бесконечного расширения recurring Activities.

## ActivityOccurrence

Concrete scheduled instance Activity template.

Инварианты:

- unique `(activity_uid, starts_at)`;
- materialization только в rolling horizon до 45 дней;
- cancelled Activity не создаёт новые occurrences;
- удаление Activity каскадно удаляет occurrence rows;
- recurring template остаётся canonical;
- repeated materialization идемпотентна;
- monthly recurrence считается от исходного calendar anchor и не накапливает drift после февраля/коротких месяцев.

`GET` не материализует данные. Materialization — отдельная command operation через `POST .../sync`.

## Reminder preference

Reminder — приватное Account state и всегда opt-in.

Allowlisted lead time:

- 15 минут;
- 60 минут;
- 1 день.

Manager Space не видит preferences участников. Reminder не меняет RSVP, reputation, discovery или achievements.

Активных reminder preferences на Account допускается не больше 200 — лимит совпадает с bounded reconciliation pass, поэтому preferences не могут постоянно выпадать за пределы query limit.

## Notification inbox

`UserNotification` — private Account-owned inbox entry.

Первый kind: `activity_reminder`.

Свойства:

- idempotent account-scoped dedupe;
- snapshot title/body сохраняет смысл истории;
- Space/Activity/Occurrence context используется только для navigation;
- context FK использует `SET NULL`, поэтому удаление исходного Activity не стирает уже полученное уведомление;
- read/unread;
- нет cross-account read/list API.

## Reconciliation

`POST /notifications/v1/sync` — явная command operation.

Для каждого разрешённого reminder backend повторно проверяет Account и active membership/ownership, materialize-ит bounded occurrence window, выбирает наступившее reminder time и пишет notification через DB-level dedupe. Очень старые occurrences не создают delayed spam.

GET endpoints состояния не создают.

Dedupe рассчитан как один reminder на concrete occurrence. Изменение lead time не создаёт второй notification для того же occurrence.

## API

- `GET /activity-occurrences/v1/activities/{activity_uid}` — прочитать materialized occurrences;
- `POST /activity-occurrences/v1/activities/{activity_uid}/sync` — явно materialize bounded window;
- `POST /notifications/v1/sync` — reconcile свои reminders;
- `GET /notifications/v1/unread-count`;
- `GET /notifications/v1`;
- `GET /notifications/v1/spaces/{space_uid}/reminders`;
- `PUT /notifications/v1/activities/{activity_uid}/reminder`;
- `DELETE /notifications/v1/activities/{activity_uid}/reminder`;
- `PATCH /notifications/v1/{notification_uid}/read`;
- `POST /notifications/v1/read-all`.

## SPA UX

- reminder control внутри Activity;
- один batch request загружает reminder state всего Space — без HTTP N+1;
- lead presets: 15 минут / час / день;
- личный экран `/notifications`;
- loading/error/empty/read states;
- переход из notification в обычный Space Life route;
- спокойный bell/unread badge в app shell;
- sync при восстановлении authenticated shell и периодически во время активной сессии;
- mobile bottom navigation не перегружена notification item.

UI правила: [`ui-ux-notifications.md`](ui-ux-notifications.md).

## Delivery boundary

`0.5.2-alpha.1` обеспечивает in-app reminders. Background browser/native push в этот checkpoint не входит.

Business rules находятся в backend reconciliation service, поэтому будущий worker/native push adapter сможет использовать тот же домен без переноса правил в Vue.

## Privacy / anti-spam invariants

- reminders opt-in;
- preferences принадлежат только Account;
- один notification максимум на occurrence;
- Account должен сохранять актуальный доступ к Space для reconciliation;
- notification context не является пропуском в Space;
- нет streak, score, engagement reward или urgency-pressure механик;
- no cross-account inbox API;
- bounded preferences + bounded occurrence horizon обеспечивают bounded work per sync.

## Calendar limitation

Activity принимает datetime с timezone и нормализует durable instant в UTC, но IANA timezone name пока не хранится. Recurrence остаётся UTC-anchored; при DST локальное wall-clock время weekly/monthly серии может сдвинуться. DST-correct semantics входят в pre-beta hardening.

## Release gate

`0.5.2-alpha.1` проходит два gate: functional exact-head CI, затем version bump/documentation sync и повторный exact-head CI. Merge разрешён только после второго зелёного gate.
