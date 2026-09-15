# PubChat Stage 5.3 — Activity Occurrences & Notifications

Development line after `0.5.1-alpha.1`: `0.5.2-alpha.x`.

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

## Reminder preference

Reminder — приватное Account state и всегда opt-in.

Allowlisted lead time:

- 15 минут;
- 60 минут;
- 1 день.

Manager Space не видит preferences участников. Reminder не меняет RSVP, reputation, discovery или achievements.

Активных reminder preferences на Account допускается не больше 200 — этот лимит совпадает с bounded reconciliation pass, поэтому старые preferences не могут голодать за пределами query limit.

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

Для каждого разрешённого reminder:

1. backend повторно проверяет Account и текущее active membership/ownership;
2. materialize-ит bounded occurrence window;
3. выбирает occurrence, для которого наступило reminder time;
4. не создаёт слишком старые delayed reminders за пределами grace window;
5. пишет notification через DB-level dedupe;
6. commit выполняется server-side.

GET endpoints не создают состояние.

Dedupe рассчитан как один reminder на concrete occurrence. Изменение lead time не создаёт второй notification для того же occurrence.

## Реализованный API

- `GET /activity-occurrences/v1/activities/{activity_uid}`;
- `POST /notifications/v1/sync`;
- `GET /notifications/v1/unread-count`;
- `GET /notifications/v1`;
- `GET /notifications/v1/spaces/{space_uid}/reminders`;
- `PUT /notifications/v1/activities/{activity_uid}/reminder`;
- `DELETE /notifications/v1/activities/{activity_uid}/reminder`;
- `PATCH /notifications/v1/{notification_uid}/read`;
- `POST /notifications/v1/read-all`.

## Реализованный SPA UX

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

`0.5.2` обеспечивает in-app reminders. Background browser/native push в этот checkpoint не входит.

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

## Release gate

До `0.5.2-alpha.1`:

- additive migration graph и одна Alembic head;
- occurrence/reminder/inbox contract tests;
- frontend production build;
- notification ownership/timezone/spam/privacy self-review;
- documentation/roadmap/UI Kit sync;
- functional exact-head CI;
- version bump только после зелёного functional gate;
- второй exact-head CI на versioned release head;
- merge только после второго gate.
