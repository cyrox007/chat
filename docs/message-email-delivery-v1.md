# Unread Messenger email delivery v1

Этот документ описывает production-механику ненавязчивого email re-engagement для непрочитанных личных сообщений. Space chat намеренно не участвует во внешней offline-доставке.

## Назначение

Если Account давно отсутствует, имеет непрочитанные Messenger сообщения, подтвердил email и явно включил `email_unread_dm_nudge`, внешний worker может сформировать одно агрегированное напоминание. Письмо не содержит текст приватных сообщений и не отправляется на каждое новое сообщение.

## Поток

1. Candidate worker по durable cursor выбирает только inactive Account с unread DM и opt-in.
2. Перед queue повторно проверяются Redis presence, Account block/privacy и текущий verified email.
3. В `external_delivery_ledger` создаётся privacy-minimal `pending` запись: counts, aggregate/dedupe keys и retry metadata; адрес и message body не сохраняются.
4. Delivery worker атомарно claim-ит bounded batch через `FOR UPDATE SKIP LOCKED`, назначает lease/token и увеличивает attempt count.
5. Непосредственно перед SMTP отправкой повторно проверяются opt-in, verified destination, текущие unread DM/block/privacy и online presence.
6. При успехе ledger становится `delivered`; временная provider ошибка получает exponential backoff; terminal error становится `failed`; opt-out/read/block transition — `suppressed`.
7. Если пользователь снова online, claim возвращается в `pending` без расходования retry budget и проверяется позднее.

## Delivery guarantees

PostgreSQL ledger — durable source of truth. Redis используется только для текущего presence. Lease позволяет другому worker восстановить запись после crash.

SMTP не даёт exactly-once guarantee. PubChat использует стабильный RFC `Message-ID` на delivery UID, чтобы повтор после crash был узнаваемым downstream, но не заявляет абсолютную дедупликацию у почтового провайдера.

## SMTP

Обязательные настройки перед включением worker:

- `MESSAGE_EMAIL_SMTP_HOST`;
- `MESSAGE_EMAIL_FROM_EMAIL`;
- либо STARTTLS, либо implicit SSL, но не оба одновременно;
- username/password задаются парой или не задаются для trusted relay.

`ops/install-message-email-worker.sh` валидирует security/realtime/SMTP settings, устанавливает systemd service/timer и выполняет один bounded пробный цикл.

Timer запускает worker примерно раз в 15 минут. Повторный systemd invocation не накладывается на уже работающий oneshot service; database cursor/claim locks дополнительно защищают multi-host concurrency.

## Privacy / anti-abuse

- offline email касается только Messenger;
- Account block и receiver DM policy проверяются на queue и непосредственно перед delivery;
- legacy `PrivateMessage`/`RoomMember` UIDs преобразуются через `Account.legacy_user_uid`, а Account policy никогда не сравнивается с legacy User UID напрямую;
- тело приватного сообщения и destination email не сохраняются в delivery ledger;
- email содержит только агрегированные counts и ссылку на Messenger;
- re-engagement channel opt-in и имеет cooldown.
