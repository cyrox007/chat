# Message notification delivery v1

Документ фиксирует delivery-модель уведомлений о сообщениях PubChat. Он расширяет notification domain из Stage 5.3 и не меняет privacy/block/access rules: уведомление никогда не расширяет право читать сообщение или Space.

## Implementation status

Baseline slices 1–2 выпущены как `0.6.7-alpha.1`:

- ✅ account-level message notification preferences + deterministic online/offline/active-context policy tests;
- ✅ Redis-backed connection-scoped Messenger active context, Space active context через distributed room presence и sound mapping в SPA;
- ✅ online-only Space alerts с membership/block boundaries;
- ✅ offline Space external re-engagement запрещён server-side policy;
- ⏳ durable email delivery ledger + scheduled unread-DM nudge worker;
- ⏳ provider abstraction/retry/backoff/metrics;
- ⏳ Web Push subscription/delivery adapter и browser/device matrix.

## Базовая матрица

Сервер определяет online/offline не по открытой вкладке, а по distributed presence в Redis. Пользователь считается online, если у Account есть хотя бы одно живое realtime-соединение PubChat на любом worker/device.

| Получатель | Messenger / direct message | Space chat |
| --- | --- | --- |
| Offline | unread/message state сохраняется; внешние delivery adapters разрешены только по opt-in | не отправлять внешнее уведомление и не создавать re-engagement pressure |
| Online где-либо в PubChat | realtime/in-app notification; разрешён звук private message | realtime/in-app notification; разрешён звук chat message |
| Online и уже смотрит тот же conversation/room | обновить message state/unread semantics по контракту клиента, но не дублировать навязчивый toast/sound поверх видимого сообщения | то же правило |

Таким образом, offline re-engagement относится только к Messenger. Space chat не должен превращаться в источник почтового/push-спама для отсутствующего пользователя.

## Presence и active context

Redis presence отвечает только на вопрос «Account сейчас подключён к PubChat?». Для подавления дублей поверх уже открытого диалога используется отдельный ephemeral active-context signal для Messenger; Space использует уже существующий distributed room presence.

Active context:

- не является durable user state;
- имеет TTL/heartbeat и исчезает при disconnect;
- хранится/разрешается через Redis realtime layer;
- используется только для delivery UX, а не для permissions/visibility;
- не должен раскрывать другим пользователям, какой экран сейчас открыт у Account.

Messenger active context connection-scoped: один device может смотреть конкретный диалог, а другой — другой экран. Server-side policy подавляет дополнительный alert, если хотя бы одно живое соединение получателя уже смотрит нужный conversation.

## Звуки

В repository используются:

- `/sounds/private_notification.mp3` — Messenger/direct message;
- `/sounds/chat_notification.mp3` — Space chat.

Звук воспроизводится только клиентом и только когда событие прошло delivery policy. Клиент обязан учитывать browser autoplay restrictions, user mute/preferences, active context и состояние видимости вкладки. Сервер не предполагает, что наличие realtime-соединения означает возможность проиграть audio.

## Preferences

Account-level `MessageNotificationPreference` хранит независимые настройки:

- Messenger in-app/realtime notifications;
- Space chat in-app notifications while online;
- Messenger sound;
- Space chat sound;
- unread Messenger email nudge;
- Web Push Messenger;
- Web Push Space flag для будущего adapter policy.

Текущий baseline API:

```text
GET   /notifications/v1/message-preferences
PATCH /notifications/v1/message-preferences
```

External/re-engagement defaults выключены. Отключение внешнего adapter не отключает сам unread/message state. Наличие preference для будущего Space Web Push не разрешает offline Space re-engagement: текущая server-side policy возвращает для offline Space external delivery `false`.

## Unread Messenger nudge по email

Первый внешний re-engagement adapter — email для непрочитанных direct messages.

Worker запускается внешним scheduler, а не внутри каждого FastAPI worker. Он выбирает Account только если одновременно выполняются условия:

1. есть непрочитанные сообщения Messenger;
2. Account отсутствует дольше configurable inactivity threshold;
3. после последнего nudge появились новые unread либо истёк configurable cooldown;
4. пользователь явно разрешил email message reminders;
5. sender/block/privacy rules всё ещё позволяют соответствующий conversation;
6. для этого unread window ещё не был отправлен эквивалентный delivery event.

Nudge должен быть ненавязчивым: агрегированный digest/count, без FOMO/streak copy и без бесконечного письма на каждый message. По умолчанию письмо не раскрывает полный текст приватных сообщений; достаточно сообщить о непрочитанных диалогах и безопасно привести пользователя в PubChat.

После возврата/прочтения cooldown state сбрасывается естественным образом. Точная частота не зашивается в product contract до load/engagement testing: threshold и cooldown конфигурируемые и имеют безопасные минимумы.

## Delivery state и idempotency

Внешняя доставка должна иметь durable ledger/state, отдельный от realtime pub/sub. Минимально нужны:

- channel: `email`, позднее `web_push`;
- notification/message aggregate key;
- Account UID;
- created/attempted/delivered/failed timestamps;
- retry count/next attempt;
- provider message id без секретов;
- dedupe key;
- failure class без утечки message contents.

PostgreSQL остаётся source of truth для unread/delivery ledger. Redis используется для presence/active context и не превращает delivery history в ephemeral state.

## Web Push / PWA

Следующий adapter после email — standards-based Web Push поверх существующего service worker:

- Push API + Notifications API + Service Worker;
- subscription привязана к Account/device и может быть отозвана;
- permission запрашивается только после явного действия пользователя, не при первом открытии сайта;
- VAPID/private keys остаются только на server side;
- payload минимальный и privacy-safe; полное содержание сообщения не требуется;
- push click открывает разрешённый destination, после чего backend заново проверяет auth/privacy/block state;
- expired/unsubscribed endpoints удаляются после terminal provider response.

На iOS/iPadOS Web Push поддерживается для web app, добавленного на Home Screen (начиная с 16.4); permission должен запрашиваться из пользовательского действия. Поэтому mobile UX должен уметь объяснить установку PWA, но не давить на пользователя.

## Anti-abuse и privacy

- Account block применяется до notification creation/delivery;
- sibling Persona не позволяет обойти Account block;
- Space moderation role не даёт доступа к приватному Messenger notification state;
- notification body не является authorization token;
- active-context suppression не является authorization decision;
- external delivery не раскрывает sender/message content сверх необходимого;
- rate limit применяется на Account/channel и aggregate window;
- отсутствие пользователя не является поводом уведомлять его о каждом сообщении Space.

## Implementation slices

1. ✅ Message-notification domain + preferences + deterministic policy tests — `0.6.7-alpha.1`.
2. ✅ Redis active-context signal и sound mapping в SPA — `0.6.7-alpha.1`.
3. ⏳ Durable email delivery ledger + scheduled unread-DM nudge worker.
4. ⏳ Email adapter/provider abstraction и retry/backoff/metrics.
5. ⏳ Web Push subscription model, VAPID adapter, service-worker push/click flow.
6. ⏳ Browser/device matrix: Chromium, Firefox, Safari macOS и iOS/iPadOS installed PWA.
