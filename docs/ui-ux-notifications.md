# PubChat UI/UX — напоминания и уведомления

Этот документ расширяет основной [`ui-ux-kit.md`](ui-ux-kit.md) правилами для notification surfaces.

## Принцип

Уведомления PubChat помогают вернуться к выбранному пользователем социальному контексту, а не создают искусственную тревожность.

Поэтому:

- reminders только opt-in;
- нет streak/FOMO copy;
- нет красного alarm badge по умолчанию;
- нет автоматического browser permission prompt;
- unread count — информационный сигнал, не оценка пользователя;
- manager Space не видит личные reminder preferences участников.

## App-shell indicator

Bell находится в top bar и не занимает один из четырёх основных mobile bottom-nav slots.

Состояния:

- `0 unread` — обычная иконка без badge;
- `1..99` — компактный badge;
- `100+` — `99+`, чтобы badge не ломал layout;
- network error — bell остаётся доступным, shell не превращает локальную ошибку inbox в global failure.

ARIA label должен сообщать число непрочитанных текстом.

## Reminder control

Reminder control находится внутри Activity, рядом с RSVP, потому что напоминание относится к конкретному социальному поводу.

Доступные presets:

- за 15 минут;
- за час;
- за день.

Первое действие — явное «Напомнить». Никакое значение не включается автоматически.

При включённом reminder пользователь может изменить lead time или отключить reminder.

## Inbox

Экран называется «Напоминания», а не «Центр внимания», «Срочное» и т.п.

Обязательные состояния:

- syncing/loading;
- список;
- unread/read;
- empty;
- recoverable network error;
- mark read;
- read all.

Empty state объясняет, где включить reminders, без давления.

## Навигация

Notification может вести в Space Life, но не является authorization token. После перехода backend снова применяет обычные visibility/membership/restriction rules.

Если доступ к Space утрачен, UI должен показать обычный permission/not-found state, а не пытаться восстановить доступ из notification context.

## Частота sync

SPA может выполнять idempotent reconciliation при восстановлении authenticated shell и периодически во время активной сессии. Частый polling ради badge не нужен.

Первый web slice не обещает background OS push. Native/browser push добавляется позже как delivery adapter поверх того же backend notification domain.

## Anti-patterns

Не использовать:

- countdown anxiety;
- «Вы потеряете серию»;
- красный badge как default;
- автоподписку на все Activities;
- reminder на Activity без активного membership;
- ranking/reputation bonus за открытие notifications;
- пуши как способ обойти block/privacy.
