# Message notification delivery v1

Документ фиксирует delivery-модель уведомлений о сообщениях PubChat. Он расширяет notification domain из Stage 5.3 и не меняет privacy/block/access rules: уведомление никогда не расширяет право читать сообщение или Space.

## Implementation status

Message policy/active-context baseline выпущен как `0.6.7-alpha.1`, durable unread-Messenger email delivery — как `0.6.8-alpha.1`:

- ✅ account-level message notification preferences + deterministic online/offline/active-context policy tests;
- ✅ Redis-backed connection-scoped Messenger active context, Space active context через distributed room presence и sound mapping в SPA;
- ✅ online-only Space alerts с membership/block boundaries;
- ✅ offline Space external re-engagement запрещён server-side policy;
- ✅ durable email delivery ledger + scheduled unread-DM candidate worker;
- ✅ SMTP provider abstraction + expiring claims + retry/backoff + systemd scheduler;
- ⏳ Web Push subscription/delivery adapter и browser/device matrix;
- ⏳ delivery/provider metrics и preferences UI для external channels.

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

Первый внешний re-engagement adapter — email для непрочитанных direct messages; production runtime закреплён checkpoint `0.6.8-alpha.1`.

Worker запускается внешним systemd timer, а не внутри каждого FastAPI worker. Candidate queue создаётся только когда одновременно выполняются условия:

1. есть непрочитанные сообщения Messenger;
2. Account отсутствует дольше configurable inactivity threshold;
3. с предыдущего не-suppressed nudge истёк Account-level configurable cooldown — новое сообщение само по себе cooldown не обходит;
4. пользователь явно разрешил email message reminders;
5. есть текущий verified email;
6. sender/block/privacy rules всё ещё позволяют соответствующий conversation;
7. Account сейчас offline по distributed Redis presence.

Перед SMTP send worker повторно проверяет online state, preference, verified destination, unread state и block/privacy. Поэтому пользователь, который вернулся, прочитал сообщения, отозвал opt-in или заблокировал отправителя между queue и delivery, не получает устаревшее письмо.

Nudge ненавязчивый: агрегированный unread/dialog count, без FOMO/streak copy и без письма на каждый message. Полный текст приватных сообщений не включается в email.

## Delivery state и idempotency

PostgreSQL `external_delivery_ledger` — durable source of truth для внешней доставки. Он хранит:

- channel + Account UID;
- aggregate/dedupe key;
- unread/dialog counts;
- pending/processing/delivered/failed/suppressed state;
- attempt count, next attempt, claim token/expiry;
- provider message id и privacy-safe failure class;
- lifecycle timestamps.

Ledger намеренно не хранит destination email и private message body. Адрес разрешается из текущего verified `Credential` непосредственно перед provider call.

Worker использует `FOR UPDATE SKIP LOCKED` и expiring claim lease. Claim берётся непосредственно перед обработкой одной записи, поэтому медленный SMTP batch не заставляет leases следующих элементов истекать раньше времени. Expired claim может быть восстановлен другим worker после crash.

Retryable provider failures получают bounded exponential backoff; terminal failures завершаются как `failed`; opt-out/read/block transition — `suppressed`. Возврат пользователя online переносит запись обратно в `pending` без расходования retry budget.

SMTP по своей природе не обеспечивает абсолютный exactly-once в crash-after-send окне. PubChat использует stable RFC Message-ID на delivery UID, но не утверждает, что внешний relay гарантированно дедуплицирует повторную попытку.

Подробный operational contract: [`message-email-delivery-v1.md`](message-email-delivery-v1.md).

## Web Push / PWA

Следующий adapter — standards-based Web Push поверх существующего service worker:

- Push API + Notifications API + Service Worker;
- subscription привязана к Account/device и может быть отозвана;
- permission запрашивается только после явного действия пользователя, не при первом открытии сайта;
- VAPID/private keys остаются только на server side;
- payload минимальный и privacy-safe; полное содержание сообщения не требуется;
- push click открывает разрешённый destination, после чего backend заново проверяет auth/privacy/block state;
- expired/unsubscribed endpoints удаляются после terminal provider response.

Mobile/iOS behavior проверяется отдельной browser/device matrix и не считается доказанным только наличием Service Worker API в коде.

## Anti-abuse и privacy

- Account block применяется до notification creation/delivery;
- sibling Persona не позволяет обойти Account block;
- Space moderation role не даёт доступа к приватному Messenger notification state;
- notification body не является authorization token;
- active-context suppression не является authorization decision;
- external delivery не раскрывает sender/message content сверх необходимого;
- re-engagement имеет Account-level cooldown;
- отсутствие пользователя не является поводом уведомлять его о каждом сообщении Space.

## Implementation slices

1. ✅ Message-notification domain + preferences + deterministic policy tests — `0.6.7-alpha.1`.
2. ✅ Redis active-context signal и sound mapping в SPA — `0.6.7-alpha.1`.
3. ✅ Durable email delivery ledger + scheduled unread-DM candidate worker — `0.6.8-alpha.1`.
4. ✅ SMTP provider + claim lease + retry/backoff + systemd scheduler — `0.6.8-alpha.1`.
5. ⏳ Web Push subscription model, VAPID adapter, service-worker push/click flow.
6. ⏳ Browser/device matrix: Chromium, Firefox, Safari macOS и installed mobile PWA scenarios.
