# Protective hold calibration v1

Checkpoint: `0.6.18-alpha.1`.

Этот документ описывает безопасный путь от полностью выключенной автоматики к возможному ограниченному production enforcement.

## Режимы

`MODERATION_PROTECTIVE_HOLDS_MODE` принимает только:

- `off` — evaluation не выполняется, restrictions не создаются;
- `shadow` — policy вычисляет, **что она сделала бы**, и сохраняет privacy-minimal evaluation, но не меняет capabilities пользователя;
- `enforce` — policy может создать только уже allow-listed короткий hold, но лишь после прохождения human-reviewed calibration gate и отдельного operational approval.

Старый `MODERATION_PROTECTIVE_HOLDS_ENABLED=true` остаётся compatibility alias для `enforce`, но больше не является достаточным условием для санкции.

## Что сохраняет shadow mode

`protective_hold_evaluations` хранит:

- source signal UID и Account UID;
- signal type;
- candidate capability;
- mode;
- policy decision;
- would-hold boolean;
- corroboration count;
- configured lookback / minimum signals / hold duration;
- timestamps.

Ledger **не хранит** message body, attachment URL, recipient list, Persona handle или private-dialog transcript.

Одна signal UID имеет одну актуальную evaluation row: повторная evaluation обновляет policy snapshot вместо накопления неограниченной истории одного dedupe bucket.

## Human labels

Moderator queue требует явную калибровочную оценку:

- `true_positive` — сигнал соответствует реальному abuse;
- `false_positive` — нормальная активность ошибочно выглядела как abuse;
- `unclear` — недостаточно уверенности; такая запись не влияет на enforcement gate.

Human label живёт на исходном abuse signal и не создаёт restriction.

## Calibration metrics

Для каждого автоматизируемого signal type считаются:

- число human-labeled would-hold candidates;
- true positives;
- false positives;
- false-positive percent;
- количество подтверждённых сигналов и доля из них, которые shadow policy поймала.

Последняя величина называется `confirmed_candidate_capture_percent` и **не является global recall**: dataset включает только уже emitted server-owned signals, которые человек разметил.

Default gate:

- минимум 25 decisive would-hold labels **для каждого** signal type;
- false-positive rate не выше 5% **для каждого** signal type;
- отдельное `MODERATION_PROTECTIVE_HOLD_ENFORCEMENT_APPROVED=true`.

Если хотя бы один signal family не проходит gate, enforce fail-closed и restriction не создаётся.

## Почему нужен отдельный approval

Даже хорошая историческая метрика не должна сама переключать платформу в punitive mode. Human Trust & Safety owner должен отдельно подтвердить включение после проверки:

- периода и репрезентативности выборки;
- false positives;
- moderator feedback;
- appeals/complaints;
- изменения traffic pattern;
- incident context.

## CLI

Проверить текущую калибровку:

```bash
cd backend
venv/bin/python3 -m workers.protective_hold_calibration --window-days 30
```

Потребовать готовность данных:

```bash
venv/bin/python3 -m workers.protective_hold_calibration --window-days 30 --require-ready
```

Exit code `2` означает, что data gate ещё не готов.

## Безопасный rollout

1. Оставить `enforcement_approved=false`.
2. Переключить MODE с `off` на `shadow`.
3. Накопить human-reviewed labels по обоим signal families.
4. Проверять CLI/dashboard минимум на согласованном observation window.
5. При приемлемой статистике сменить MODE на `enforce`, но оставить approval=false и подтвердить, что санкций всё ещё нет.
6. После отдельного human decision выставить approval=true.
7. Наблюдать active holds, false positives, appeals и moderator feedback.
8. При проблеме немедленно вернуть MODE=shadow или off; уже созданные holds истекут максимум через 15 минут.

## Что автоматике всё ещё запрещено

Calibration gate не расширяет allow-list. Автоматика не получает:

- `account.access`;
- permanent restriction;
- Space chat restriction;
- media quarantine/remove;
- profile/discovery restriction;
- revoke;
- appeal decision;
- действия против privileged Account.

## CI rehearsal

PostgreSQL integration проверяет:

- shadow candidate сохраняется;
- shadow не создаёт restriction;
- false-positive label блокирует data gate;
- исправленная human label может сделать data gate готовым;
- data-ready без operational approval всё равно не применяет hold;
- data-ready + approval разрешает только короткий allow-listed hold.

CI использует синтетические labels только для проверки механики. Они **не являются production calibration data**.
