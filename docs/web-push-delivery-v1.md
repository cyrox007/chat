# Web Push / PWA Messenger delivery v1

Checkpoint: `0.6.9-alpha.1`.

Этот документ фиксирует первый production-oriented Web Push adapter PubChat. Он продолжает message-delivery policy из `0.6.7-alpha.1` и durable external-delivery foundation из `0.6.8-alpha.1`.

## Product boundary

Web Push — внешний re-engagement канал только для Messenger/direct messages и только после явного opt-in пользователя.

Space chat не создаёт background push для offline Account. Online Space alerts остаются realtime/in-app сигналом и могут использовать `chat_notification.mp3`, но отсутствие пользователя не превращает Space traffic в внешний push-pressure.

Push не меняет authorization. Право увидеть conversation/message всё равно определяется обычными auth/privacy/block rules после открытия приложения.

## Privacy contract

Push payload намеренно минимален:

```json
{
  "type": "messenger",
  "title": "Новое сообщение в PubChat",
  "body": "У вас есть новое личное сообщение.",
  "url": "/messenger",
  "tag": "pubchat-messenger"
}
```

В payload нет:

- текста приватного сообщения;
- имени/Persona отправителя;
- email/телефона;
- access/refresh token;
- WebSocket ticket;
- произвольного внешнего URL.

Service worker принимает только same-origin navigation destination. Push notification не является authorization token.

## Subscription lifecycle

`web_push_subscriptions` хранит один browser/device subscription на Account:

- endpoint;
- SHA-256 fingerprint endpoint для lookup/uniqueness;
- Push API encryption keys `p256dh`/`auth`;
- ограниченный user-agent для operational diagnostics;
- lifecycle timestamps.

Endpoint и encryption keys считаются delivery credentials и не попадают в публичные profile/notification projections или обычные application logs.

API:

```text
GET  /notifications/v1/web-push/config
GET  /notifications/v1/web-push/subscriptions/status
POST /notifications/v1/web-push/subscriptions
POST /notifications/v1/web-push/subscriptions/remove
```

`/config` отдаёт только capability flag и VAPID public key. Private VAPID key остаётся backend-only.

Permission запрашивается только в прямом user gesture (`Включить push`). Bootstrap приложения не вызывает `Notification.requestPermission()`.

При logout/session teardown текущая local PushSubscription удаляется/отвязывается best-effort, чтобы shared browser не сохранил endpoint предыдущего Account.

## Queueing policy

Когда сохраняется новый DM, server-side policy сначала определяет online/offline через distributed Redis presence.

Web Push queue создаётся только если:

1. получатель offline;
2. `web_push_messenger=true`;
3. у Account есть хотя бы одна registered subscription;
4. conversation всё ещё разрешён block/privacy policy;
5. для того же conversation не действует configurable cooldown/dedupe window;
6. VAPID/provider config включён.

Новый DM не гарантирует новый push: per-conversation cooldown специально ограничивает pressure.

## Durable delivery

Web Push использует общий PostgreSQL `external_delivery_ledger` с channel `web_push`.

Delivery worker:

- claim-ит одну запись через `FOR UPDATE SKIP LOCKED`;
- устанавливает expiring lease/token;
- непосредственно перед provider send повторно проверяет Redis online presence, opt-in, unread state и block/privacy;
- отправляет payload во все актуальные subscriptions Account;
- terminal endpoint responses `404/410` удаляют конкретную протухшую subscription;
- retryable provider/transport failures получают bounded exponential backoff;
- stale read/opt-out/block/online transition переводит или подавляет delivery вместо отправки устаревшего push.

Как и SMTP, Web Push не обещает абсолютный exactly-once на внешней provider boundary. Durable ledger обеспечивает bounded retry/idempotency внутри PubChat, но provider/browser delivery остаётся внешней системой.

## Worker lifecycle

Worker не запускается внутри Uvicorn workers.

Ручной запуск:

```bash
cd backend
python -m workers.web_push_delivery
```

Production unit/timer:

```bash
cd /home/projects/pubchat
bash ops/install-web-push-worker.sh
```

Installer проверяет security/realtime/VAPID settings, устанавливает `pubchat-web-push.service` и `pubchat-web-push.timer`, включает timer и выполняет bounded first run.

## Configuration

Основные settings:

```text
WEB_PUSH_VAPID_PUBLIC_KEY=
WEB_PUSH_VAPID_PRIVATE_KEY=
WEB_PUSH_VAPID_SUBJECT=mailto:ops@example.com
WEB_PUSH_TTL_SECONDS=3600
WEB_PUSH_DELIVERY_BATCH_SIZE=50
WEB_PUSH_DELIVERY_MAX_ATTEMPTS=5
WEB_PUSH_DELIVERY_RETRY_BASE_SECONDS=60
WEB_PUSH_DELIVERY_RETRY_MAX_SECONDS=3600
WEB_PUSH_DELIVERY_LEASE_SECONDS=300
WEB_PUSH_CONVERSATION_COOLDOWN_SECONDS=300
```

Private key не должен попадать в frontend build, repository, logs или diagnostics output.

## Service Worker contract

`frontend/public/service-worker.js` сохраняет прежнюю cache boundary:

- navigation — network-first с cached app shell fallback;
- runtime cache — только static destinations/assets;
- API/auth/private fetch/XHR не кэшируются;
- `push` показывает privacy-safe notification;
- `notificationclick` фокусирует подходящее same-origin окно либо открывает Messenger.

Web Push не превращает PWA в offline messenger: private message history остаётся server-side.

## Browser/device limitations

Наличие Push API в коде не считается доказанной cross-browser совместимостью. До beta отдельно проверяются:

- Chromium desktop/Android;
- Firefox desktop/Android, где доступно;
- Safari macOS;
- iOS/iPadOS installed Home Screen PWA flow;
- denied/default/granted permission states;
- unsubscribe/expired endpoint;
- logout/login другим Account на том же browser profile;
- notification click при закрытом/открытом приложении.

Safari/WebKit registration/login/refresh compatibility остаётся отдельным browser gate и не смешивается с самим provider adapter.

## Security / abuse invariants

- push opt-in не расширяет DM eligibility;
- Account block проверяется до queue и перед send;
- sibling Persona не обходит Account-level block;
- Space moderator не получает доступ к push subscriptions;
- endpoint/key material не является публичным API;
- payload не раскрывает private content на lock screen;
- Web Push не используется для streak/FOMO pressure;
- offline Space chat не создаёт push delivery.

## Remaining work

- production delivery/provider metrics и alerting;
- load/idempotency profiling на большем количестве subscriptions;
- real browser/device matrix, особенно Safari/iOS installed-PWA flow;
- notification UX/accessibility review;
- operational runbook для VAPID rotation и provider outage.
