# Message notification delivery v1

Документ фиксирует целевую delivery-модель уведомлений о сообщениях PubChat. Он расширяет notification domain из Stage 5.3 и не меняет privacy/block/access rules: уведомление никогда не расширяет право читать сообщение или Space.

## Базовая матрица

Сервер определяет online/offline не по открытой вкладке, а по distributed presence в Redis. Пользователь считается online, если у Account есть хотя бы одно живое realtime-соединение PubChat на любом worker/device.

| Получатель | Messenger / direct message | Space chat |
| --- | --- | --- |
| Offline | создать unread/message notification; разрешены внешние delivery adapters по настройкам | не отправлять внешнее уведомление и не создавать re-engagement pressure |
| Online где-либо в PubChat | realtime/in-app notification; разрешён звук private message | realtime/in-app notification; разрешён звук chat message |
| Online и уже смотрит тот же conversation/room | обновить message state/unread semantics по контракту клиента, но не дублировать навязчивый toast/sound поверх видимого сообщения | то же правило |

Таким образом, offline re-engagement относится только к Messenger. Space chat не должен превращаться в источник почтового/push-спама для отсутствующего пользователя.

## Presence и active context

Redis presence отвечает только на вопрос «Account сейчас подключён к PubChat?». Для подавления дублей поверх уже открытого диалога нужен отдельный ephemeral active-context signal: `messenger:<dialog_uid>` или `space:<space_uid>`.

Active context:

- не является durable user state;
- имеет TTL/heartbeat и исчезает при disconnect;
- хранится в Redis вместе с realtime presence;
- используется только для delivery UX, а не для permissions/visibility;
- не должен раскрывать другим пользователям, какой экран сейчас открыт у Account.

## Звуки

В repository уже существуют:

- `/sounds/private_notification.mp3` — Messenger/direct message;
- `/sounds/chat_notification.mp3` — Space chat.

Звук воспроизводится только клиентом и только когда событие прошло delivery policy. Клиент обязан учитывать browser autoplay restrictions, user mute/preferences, active context и состояние видимости вкладки. Сервер не предполагает, что наличие realtime-соединения означает возможность проиграть audio.

## Unread Messenger nudge по email

Первый внешний re-engagement adapter — email для непрочитанных direct messages.

Worker запускается внешним scheduler, а не внутри каждого FastAPI worker. Он выбирает Account только если одновременно выполняются условия:

1. есть непрочитанные сообщения Messenger;
2. Account отсутствует дольше configurable inactivity threshold;
3. после последнего nudge появились новые unread либо истёк configurable cooldown;
4. пользователь не отключил email message reminders;
5. sender/block/privacy rules всё ещё позволяют соответствующий conversation;
6. для этого unread window ещё не был отправлен эквивалентный delivery event.

Nudge должен быть ненавязчивым: агрегированный digest/count, без FOMO/streak copy и без бесконечного письма на каждый message. По умолчанию письмо не должно раскрывать полный текст приватных сообщений; достаточно сообщить о непрочитанных диалогах и безопасно привести пользователя в PubChat.

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

## Preferences

NotificationPreference должен быть расширен минимум следующими независимыми настройками:

- Messenger in-app/realtime notifications;
- Space chat in-app notifications while online;
- Messenger sound;
- Space chat sound;
- unread Messenger email nudge;
- Web Push Messenger;
- Web Push Space chat while online/offline policy остаётся отдельным продуктовым решением.

Default не должен автоматически включать маркетинговые/re-engagement каналы без явного product/legal решения. Отключение внешнего adapter не отключает сам inbox/unread state.

## Anti-abuse и privacy

- Account block применяется до notification creation/delivery;
- sibling Persona не позволяет обойти Account block;
- Space moderation role не даёт доступа к приватному Messenger notification state;
- notification body не является authorization token;
- external delivery не раскрывает sender/message content сверх необходимого;
- rate limit применяется на Account/channel и aggregate window;
- отсутствие пользователя не является поводом уведомлять его о каждом сообщении Space.

## Implementation slices

1. Message-notification domain + preferences + deterministic policy tests.
2. Redis active-context signal и sound mapping в SPA.
3. Durable email delivery ledger + scheduled unread-DM nudge worker.
4. Email adapter/provider abstraction и retry/backoff/metrics.
5. Web Push subscription model, VAPID adapter, service-worker push/click flow.
6. Browser/device matrix: Chromium, Firefox, Safari macOS и iOS/iPadOS installed PWA.
