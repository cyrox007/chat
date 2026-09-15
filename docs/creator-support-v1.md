# PubChat Stage 5.4 — Creator Support & Cosmetic Gifts

Development line after `0.5.2-alpha.1`: `0.5.3-alpha.x`.

## Зачем нужен этот slice

PubChat позволяет благодарить людей и поддерживать атмосферу Spaces, но не превращает деньги или количество подарков в социальную власть.

Первый support slice намеренно **не является платёжной системой**. Он вводит consent-first social gifts, append-only history и cosmetic entitlements без checkout, wallet, currency, price, paid ranking или purchaseable permissions.

## Базовые инварианты

- support всегда opt-in для Persona и Space;
- gift — социальный gesture, а не единица валюты;
- количество gifts не является рейтингом Persona/Space;
- support не влияет на trust, moderation authority, scoped roles, permissions, discovery ranking или ban/appeal outcome;
- sender не получает score, streak, rank или reward за отправку;
- Account-level block нельзя обойти gift API;
- profile visibility применяется до Persona gift/shelf projection;
- Space gift требует актуальное active membership;
- owner не может отправлять gifts собственному Space;
- self-gift Persona запрещён;
- один Account может отправить не более 20 внутренних gifts за rolling 24h;
- реальные payments не входят в `0.5.3`.

## Consent settings

### Persona

`CreatorSupportProfile` принадлежит Account и применяется к primary Persona текущей Identity v2.

Поля:

- `enabled` — разрешено ли другим людям отправлять gifts;
- `note` — короткая необязательная подпись владельца.

По умолчанию support выключен.

### Space

`SpaceSupportSettings` принадлежит Space. Изменять settings могут только scoped owner/moderator. По умолчанию support выключен.

## Gift catalog

`GiftDefinition` — allowlisted server-owned каталог.

Первый набор:

- `applause` 👏;
- `bouquet` 💐;
- `lantern` 🏮;
- `spark` ✨;
- `warm_cup` ☕.

Каждый gift имеет target scope `persona`, `space` или `both`.

В модели и writable DTO отсутствуют `price`, `amount`, `currency`, `balance`, `points`, `score`, `rank`, `trust`, `role`, `permission`, `payment`, `winner`, `prize`.

## Append-only support ledger

`SupportLedgerEntry` фиксирует факт социального gesture.

Хранятся sender reference, target kind, optional live Persona/Space reference, snapshot target label, snapshot sender label, gift code, optional message и timestamp.

Ledger не имеет PATCH/DELETE API. Target foreign keys используют `SET NULL`, поэтому удаление Persona/Space не переписывает историю. Snapshot labels сохраняют человеческий смысл старой записи.

DB constraint запрещает несовместимую вторую target reference, но разрешает historical row без live target после `SET NULL`.

## Cosmetic entitlement

Каждый отправленный gift создаёт `CosmeticEntitlement` для живой Persona или Space.

Entitlement:

- отделён от ledger history;
- привязан ровно к одной живой цели;
- не является permission/trust/reputation;
- удаляется вместе с Persona/Space;
- не создаёт доступ к закрытому профилю или Space.

## Visibility model

### Public shelf

Публичная projection показывает только gift icon/name/description и aggregate count.

Публичный shelf **не показывает** sender, message, время отправки или support ledger UID и не является leaderboard.

### Private Persona history

Владелец Account может видеть свою полученную историю с sender label/message. Чужой Account не имеет API для этой истории.

### Private Space history

Scoped owner/moderator может видеть received history своего Space. Обычный member/visitor — нет.

## Abuse boundaries

- maximum 20 gifts per Account / rolling 24h;
- support disabled отклоняет отправку server-side;
- inactive/deleted Account не может отправлять gift;
- blocked Persona pair не может взаимодействовать через support;
- Space sender должен оставаться active member на момент отправки;
- public shelf агрегирован и не создаёт sender-presence side channel;
- messages не выводятся в публичный shelf;
- нет urgency timers, streaks, jackpot/confetti и donor leaderboard.

Rate-limit первого бесплатного slice является anti-spam boundary, а не financial fraud control. Перед реальными payments потребуется отдельная transaction/idempotency/fraud/chargeback модель.

## Реализованный API

Prefix: `/support/v1`.

Реализованы:

- gift catalog;
- own Persona support settings;
- own received history;
- Persona shelf по Persona UID и Account UID + send gift;
- Space support settings;
- Space shelf + send gift;
- manager-only Space received history.

Support ledger не имеет mutation endpoints.

## Реализованный SPA UX

### Persona

- opt-in toggle и note в «Стиле образа»;
- собственная private received history;
- aggregated shelf в обычном Persona profile;
- gift picker для допустимого viewer.

### Space

- отдельный `/spaces/:uid/support` context route;
- aggregated shelf;
- gift picker только при active membership и enabled support;
- manager settings + private received history;
- контекстная ссылка «Поддержка» в desktop/app menu;
- mobile bottom navigation не получает отдельный support item.

## Financial boundary

`0.5.3` не содержит checkout, payment provider, wallet, internal currency, balances, withdrawals/payouts, refunds/chargebacks, paid discovery, paid trust, paid moderation role или paid ban immunity.

Если позже появятся реальные payments, они добавляются отдельным review и отдельными contracts поверх существующего social-support домена, а не через превращение gift count в социальный рейтинг.

## Release gate

До `0.5.3-alpha.1`:

- additive migration graph и одна Alembic head;
- support contract regression tests;
- backend compile/import;
- frontend production build;
- abuse/privacy/permissions self-review;
- docs/UI Kit sync;
- functional exact-head CI;
- version bump только после зелёного functional gate;
- второй exact-head CI на versioned head;
- squash merge только после второго gate.
