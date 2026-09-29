# Moderation privacy projection v1

Checkpoint: `0.6.29-alpha.1`.

PubChat хранит moderation records на уровне Account, но пользовательские API не должны превращать эту внутреннюю связь в способ коррелировать Persona между собой.

## Основной принцип

Один durable moderation record может иметь несколько представлений:

- **reporter-facing** — только данные собственной жалобы и публичный результат;
- **restriction-target-facing** — только данные, необходимые для понимания/апелляции санкции;
- **moderator-only** — operational identity, report linkage, internal taxonomy и assignment, необходимые для Trust & Safety workflow.

Privileged projection не должен переиспользоваться в публичном endpoint «для удобства».

## Reporter-facing reports

Reporter может видеть UID объекта, на который он сам пожаловался: например, Persona или message source UID. Это не считается новой disclosure — объект уже был известен пользователю.

Нельзя дополнительно выводить через moderation Account linkage:

- target Account UID;
- другую или primary Persona target Account;
- moderator/assignee Account UID;
- queue priority;
- internal resolution code/taxonomy.

Это особенно важно для модели нескольких Persona: жалоба на Persona A не должна раскрывать Persona B того же Account.

## Restriction target-facing view

Account, к которому применено ограничение, получает:

- restriction UID;
- capability;
- platform/Space scope;
- public explanation;
- effective status;
- start/expiry/revoke/created timestamps.

Не возвращаются:

- moderator actor Account UID;
- target Account UID;
- linked report UID;
- internal reason code;
- human/automation origin;
- authority snapshots.

Эти поля не требуются для подачи апелляции и раскрывают внутреннюю структуру moderation system.

## Moderator-only view

Привилегированный moderation workflow может получать Account/report/actor/target/reason/origin metadata там, где endpoint защищён platform moderation permissions.

Разделение projection не отменяет server-side RBAC и hierarchy checks.

## Appeals

User-facing appeal projection сохраняет текст собственной апелляции, публичную restriction information, status/resolution и timing.

Reviewer/actor Account IDs разрешены только в moderator review surface.

## UI contract

Safety Center не должен ожидать target identity из reporter-history API. История жалоб показывает category/status/description/time/public outcome, но не выполняет скрытый lookup target primary Persona.

## CI contract

Tests фиксируют:

- reporter Trust & Safety projection не содержит target Account UID, другой/primary Persona, priority, assignment или internal resolution code;
- reported source UID остаётся доступным;
- target restriction projection не содержит actor/target Account IDs, report UID, reason taxonomy или origin;
- moderator restriction projection сохраняет эти поля;
- legacy Space report history не коррелирует target Account с primary Persona;
- PostgreSQL rehearsal использует две Persona одного Account, чтобы privacy boundary проверялась не только структурно.

## Оставшийся privacy scope

Этот checkpoint не закрывает весь privacy review. Отдельно остаются:

- Account block coverage и side-channel review;
- secrets/logging review;
- cross-surface presence/activity leakage;
- export/deletion lifecycle;
- financial privacy threat model до платежей.
