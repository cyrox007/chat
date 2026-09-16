# PubChat UI/UX — напоминания и уведомления

Этот документ расширяет основной [`ui-ux-kit.md`](ui-ux-kit.md) правилами для notification surfaces. Delivery policy для сообщений подробно зафиксирован в [`message-notification-delivery-v1.md`](message-notification-delivery-v1.md).

## Принцип

Уведомления PubChat помогают вернуться к выбранному пользователем социальному контексту, а не создают искусственную тревожность.

Поэтому:

- reminders только opt-in;
- нет streak/FOMO copy;
- нет красного alarm badge по умолчанию;
- нет автоматического browser permission prompt;
- unread count — информационный сигнал, не оценка пользователя;
- manager Space не видит личные reminder preferences участников;
- offline re-engagement не рассылает пользователю каждое сообщение Space.

## Message delivery UX

Message notifications различают Messenger и Space chat.

- Если Account offline, внешнее re-engagement уведомление создаётся только для непрочитанных Messenger/direct messages.
- Если Account online где-либо в PubChat, realtime/in-app notification может приходить и для Messenger, и для Space chat.
- Если пользователь уже смотрит тот же dialog/Space room, visible message не должен дублироваться навязчивым toast/sound.
- Online определяется distributed Redis presence; active room/dialog — отдельный ephemeral client context и не является privacy-visible статусом.

Для звука используются уже существующие assets:

- `private_notification.mp3` — Messenger;
- `chat_notification.mp3` — Space chat.

Audio подчиняется browser autoplay policy и пользовательским настройкам. Неудача воспроизведения звука не является ошибкой доставки сообщения.

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

## Ненавязчивое возвращение в Messenger

Если пользователь долго не заходил и у него остаются непрочитанные direct messages, внешний scheduler позднее может отправить агрегированное email-напоминание.

UX-правила:

- не письмо на каждое сообщение;
- configurable inactivity threshold и cooldown;
- повтор только если unread всё ещё актуален и delivery не дедуплицирован;
- без countdown, streak, «вас ждут»/«вы всё пропустили» и другого pressure copy;
- безопасный summary без полного текста приватных сообщений по умолчанию;
- понятное управление email reminders в preferences.

## Web Push / PWA

Web Push добавляется отдельным delivery adapter поверх service worker, а не отдельной notification domain.

- permission запрашивается только по пользовательскому действию;
- отказ не ухудшает базовый Messenger/in-app UX;
- push destination после открытия снова проходит backend auth/privacy checks;
- subscription можно отключить/отозвать;
- iOS/iPadOS flow должен учитывать, что Web Push относится к установленным Home Screen web apps.

## Навигация

Notification может вести в Space Life, Messenger или конкретный допустимый context, но не является authorization token. После перехода backend снова применяет обычные visibility/membership/restriction rules.

Если доступ к Space утрачен, UI должен показать обычный permission/not-found state, а не пытаться восстановить доступ из notification context.

## Частота sync

SPA может выполнять idempotent reconciliation при восстановлении authenticated shell и периодически во время активной сессии. Частый polling ради badge не нужен.

Background delivery выполняется adapter/worker слоями. Service worker не становится хранилищем приватного notification state.

## Anti-patterns

Не использовать:

- countdown anxiety;
- «Вы потеряете серию»;
- красный badge как default;
- автоподписку на все Activities;
- reminder на Activity без активного membership;
- ranking/reputation bonus за открытие notifications;
- пуши как способ обойти block/privacy;
- email/push на каждое Space chat message отсутствующему пользователю;
- автоматический notification permission prompt при первом открытии.
