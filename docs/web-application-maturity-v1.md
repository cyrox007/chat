# PubChat Stage 5.6 — Web Application Maturity

Development line: `0.5.5-alpha.x`.

## Цель

Сделать текущий Vue SPA более похожим на законченное приложение: installable PWA shell, предсказуемое offline-поведение, централизованный lifecycle уведомлений и отдельный reminder worker, который не зависит от открытого браузера.

Stage 5.6 не превращает PubChat в offline messenger и не добавляет browser/native push. Он создаёт безопасную основу для дальнейшего web/native delivery.

## PWA installability

Production build регистрирует `/service-worker.js`. Development Vite не регистрирует service worker, чтобы cache не мешал разработке.

Web manifest использует существующие 192x192 и 512x512 icons и standalone display mode.

UI показывает спокойный install prompt только когда браузер сообщает `beforeinstallprompt`. Отказ «Не сейчас» действует только в текущей browser session.

## Offline contract

Offline поддержка означает **application shell**, а не offline-доступ к приватным данным.

Service worker может кэшировать:

- navigation shell (`/`, `/index.html`);
- manifest и icons;
- same-origin static assets Vite;
- static image/font/style/script destinations.

Service worker намеренно не кэширует:

- API/fetch/XHR responses;
- auth/session endpoints;
- notifications inbox;
- Persona/Space private projections;
- messages;
- realtime/WebSocket data;
- access/refresh credentials.

Navigation использует network-first strategy с fallback на cached shell. Static assets используют bounded runtime cache semantics.

Если сеть пропала после загрузки приложения, текущий уже отрисованный экран остаётся открыт. Это не означает, что данные этого экрана гарантированно восстановятся после закрытия/перезапуска браузера без сети.

## Service worker security boundary

Browser access JWT остаётся memory-only. Service worker не является дополнительным хранилищем identity/session state.

CI guard `npm run check:pwa` проверяет manifest/installability и запрещённый cache path для generic fetch/XHR/API requests.

## Application update UX

При установке новой версии service worker SPA показывает нейтральное уведомление «Доступно обновление PubChat». Пользователь сам запускает reload. Update banner использует polite live region и keyboard-visible controls.

## Notification client lifecycle

Notification state вынесен из Header в отдельный Vuex module.

`App.vue` владеет authenticated lifecycle:

- sync после успешного восстановления identity;
- periodic polling пока Account authenticated;
- stop/reset при logout/session expiry;
- reconciliation после возвращения сети;
- один in-flight authenticated bootstrap, чтобы auth watcher и initial mount не создавали двойное подключение.

Header только отображает unread state. Notifications screen обновляет тот же store после read/read-all.

CI guard `npm run check:lifecycle` закрепляет эту границу и не позволяет вернуть interval/API ownership в Header.

## Reminder worker

Reminder reconciliation больше не обязана выполняться только из открытого SPA.

CLI:

```bash
cd backend
python -m workers.notification_reconciler
```

Worker должен запускаться внешним scheduler'ом: cron, systemd timer, Kubernetes CronJob или аналогом.

Worker **не запускается** из FastAPI lifespan и не создаёт background loop в каждом Uvicorn process.

### Bounded processing

Один run ограничен `batch_size` и `max_batches`. Это защищает БД от бесконечного sweep.

`NotificationWorkerState` хранит durable cursor. Следующий bounded run продолжает после последнего обработанного Account вместо постоянного старта с начала списка.

### Concurrency

Worker state читается через PostgreSQL row lock `FOR UPDATE SKIP LOCKED`. Если другой reconciler уже держит lease-row, второй run пропускает цикл вместо параллельного sweep.

Если process падает до сохранения нового cursor, часть Account может быть обработана повторно. Это безопасно: notification domain имеет idempotent DB dedupe.

После достижения конца eligible Account set cursor сбрасывается, и следующий scheduler-run начинает новый цикл.

## Что Stage 5.6 не делает

- не кэширует личные сообщения для offline reading;
- не отправляет browser push;
- не отправляет APNs/FCM native push;
- не запускает scheduler внутри FastAPI;
- не сохраняет access JWT в service worker/cache/localStorage;
- не обещает background delivery без настроенного внешнего worker scheduler;
- не заменяет production observability/load testing.

## Accessibility / UX

- install prompt имеет именованный accessible region;
- update status объявляется polite live region;
- dismiss/update controls имеют keyboard-visible focus;
- offline/reconnect notice не обещает сохранение приватных server data;
- mobile bottom navigation не расширяется PWA controls.

## Release gate

Перед `0.5.5-alpha.1`:

- одна Alembic head;
- backend compile/import/contracts;
- notification worker cursor/concurrency regressions;
- SPA security guard;
- PWA cache-safety guard;
- app lifecycle guard;
- production frontend build;
- accessibility/offline consistency review;
- docs/operations/UI Kit sync;
- functional exact-head CI;
- version bump;
- второй exact-head CI;
- merge только после второго gate.
