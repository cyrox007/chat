# Space member-capacity concurrency v1

Checkpoint `0.6.22-alpha.1` делает `member_limit` жёстким PostgreSQL-инвариантом при конкурентной активации участников.

## Проблема

Раньше direct join, invitation accept и manager approval выполняли независимую последовательность:

1. посчитать active memberships;
2. сравнить с `member_limit`;
3. активировать membership;
4. commit.

Два параллельных запроса могли оба увидеть одно свободное место и оба пройти проверку.

## Admission lock

Все переходы, способные сделать membership `active`, теперь сериализуются на одной строке `space_settings` через `SELECT ... FOR UPDATE`.

- `join_space`;
- `respond_to_invitation(..., accept)`;
- `manage_membership(..., approve)`.

Для исторических/частично мигрированных данных без `space_settings` используется fallback lock строки `rooms`, поэтому код не откатывается к racy COUNT.

После получения lock выполняется новый COUNT active memberships. Следующий конкурент получает lock только после commit/rollback предыдущего и видит уже актуальное состояние.

## Idempotency

Direct join повторно читает membership после acquisition lock. Это важно для двух одновременных запросов одного Account:

- первый создаёт membership;
- второй после ожидания видит уже `active`;
- второй возвращает существующее состояние, а не падает на `uq_space_membership`.

Manager approval после admission lock также re-lock/re-read target membership и повторяет role/status checks.

## PostgreSQL rehearsal

Интеграционный тест намеренно удерживает admission lock, запускает конкурирующие service calls и проверяет три сценария:

- direct join против invitation accept за последнее место;
- direct join против manager approval за последнее место;
- два concurrent join одного Account.

В первых двух случаях ровно один запрос активируется, второй получает `space_full`; active count не превышает `member_limit`. В третьем оба вызова идемпотентно завершаются, но membership row остаётся одна.

Тест использует bounded timeout и всегда освобождает gate transaction, поэтому настоящий deadlock превращается в быстрый CI failure.

## Дополнительный исправленный дефект

Concurrency rehearsal обнаружил, что часть `space.service` использовала `db.get(Room, space_uid)`. У `Room` primary key — integer `id`, тогда как public Space identifier — UUID `uid`.

Update/archive/join/leave/member-role paths теперь загружают активный Space явно по `Room.uid`. Contract test запрещает возврат к integer-PK lookup для публичного UUID.

## Scope

Этот checkpoint не резервирует место при создании invitation и не считает pending membership занятым местом. Capacity применяется в момент фактической активации — это намеренный контракт.
