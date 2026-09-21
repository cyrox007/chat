# External delivery observability v1

Checkpoint `0.6.19-alpha.1` добавляет первый production-oriented observability слой для внешней Messenger delivery: unread-DM email и Web Push.

## Цель

Email/Web Push уже имеют durable `external_delivery_ledger`, retry/backoff и expiring claims. До этого оператор видел в основном отдельные worker logs. Новый слой даёт агрегированную картину backlog/retry/failure без раскрытия пользовательских данных.

## Что измеряется

Для каждого channel `email` и `web_push`:

- текущий `pending_count`;
- количество delivery, которые уже должны выполняться — `due_count`;
- возраст самого старого due item;
- `processing_count`;
- количество истёкших/аномальных processing claims;
- retry pressure — записи с `attempt_count > 1` в выбранном окне;
- delivered/failed counts за окно;
- агрегированные current-status и failure-class counts.

Отдельно возвращается только общее количество зарегистрированных Web Push subscriptions.

## Health semantics

Observability не меняет delivery policy и не выполняет suppress/retry самостоятельно.

Operational health становится `false`, если:

- у email due backlog старейший item старше `EXTERNAL_DELIVERY_EMAIL_BACKLOG_ALERT_SECONDS`;
- у Web Push due backlog старейший item старше `EXTERNAL_DELIVERY_WEB_PUSH_BACKLOG_ALERT_SECONDS`;
- существует хотя бы один processing claim с отсутствующим/истёкшим `claim_expires_at`.

Default thresholds:

- email: 3600 секунд;
- Web Push: 300 секунд.

Thresholds являются alerting contract, а не SLA promise. Их нужно калибровать по реальной worker cadence и production volume.

## Admin API

Только admin:

```
GET /admin/operations/external-delivery?window_hours=24
```

Ответ содержит только агрегаты. Он не возвращает Account ID, email address, push endpoint/key material, message body, aggregate/dedupe key, claim token или provider message id.

## CLI / machine gate

```bash
cd backend
python -m workers.external_delivery_observability --window-hours 24
```

Для scheduler/monitoring:

```bash
python -m workers.external_delivery_observability --window-hours 24 --require-healthy
```

Exit code `2` означает stale due backlog или expired processing claim. Это можно использовать как внешний alerting probe.

## Structured worker logs

Email queue/delivery worker и Web Push delivery worker теперь пишут completion events как JSON payload:

- `external_delivery.email.queue_complete`;
- `external_delivery.email.delivery_complete`;
- `external_delivery.web_push.delivery_complete`.

Поля содержат только aggregate counters и infrastructure-ready state.

Helper `utils.observability.structured_event` fail-closed отклоняет чувствительные field names, включая token/secret/password/email/destination/endpoint/push keys/message body/content.

## Privacy boundary

Observability специально не является способом «посмотреть, кому и что отправляли».

Запрещено помещать в metrics/log payload:

- Account/Persona identifiers;
- destination email;
- Web Push endpoint, `p256dh`, auth key;
- access/refresh/WebSocket tokens;
- private message body;
- external-delivery aggregate/dedupe key;
- claim token;
- provider message identifier.

PostgreSQL integration test дополнительно сериализует metrics и проверяет отсутствие seeded private identifiers.

## Что этот checkpoint не доказывает

Это не полный observability stack. Здесь нет:

- независимых provider-side SMTP/Web Push availability/SLA metrics;
- общего HTTP/realtime/PostgreSQL/Redis telemetry stack;
- external metrics backend/Prometheus/Grafana;
- error tracking provider;
- pager/on-call integration.

Checkpoint закрывает именно durable external-delivery backlog/failure visibility и безопасные machine-readable operational probes. Следующие observability slices должны расширять telemetry без ослабления privacy boundary.
