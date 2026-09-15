# PubChat Stage 5.4 — Creator Support & Cosmetic Gifts

Development line: `0.5.3-alpha.x`.

## Цель

Дать пользователям спокойный способ сказать «спасибо» Persona или Space и сохранить историю поддержки, не превращая PubChat в магазин социального влияния.

Первый checkpoint **не содержит реальных платежей**. Gifts — внутренние бесплатные cosmetic gestures. Эта граница намеренна: финансовый checkout, провайдеры, refunds/chargebacks и платёжная безопасность требуют отдельного review.

## Инварианты

- support opt-in: Persona/Space сами включают получение gifts;
- gift не меняет trust, role, permissions, moderation power или discovery ranking;
- нет balance/wallet/price/currency/points/score/rank;
- Persona нельзя подарить gift самому себе;
- owner не может отправить gift собственному Space;
- Space gift требует active membership;
- Persona gift соблюдает profile privacy и Account-level block;
- не более 20 внутренних gifts с одного Account за rolling 24 часа;
- публичный shelf показывает только gift + aggregate count;
- sender/message доступны только приватной recipient/manager history;
- support ledger append-only через публичный API;
- ledger хранит snapshot labels, чтобы историческая запись сохраняла смысл после rename/delete;
- cosmetic entitlement не является authority entitlement.

## Domain model

- `CreatorSupportProfile` — opt-in и короткая публичная заметка Persona support;
- `SpaceSupportSettings` — opt-in Space;
- `GiftDefinition` — allowlisted cosmetic catalog;
- `SupportLedgerEntry` — immutable support history;
- `CosmeticEntitlement` — живой cosmetic artifact для Persona или Space.

## Начальный каталог

- ☕ Тёплая кружка — Persona/Space;
- ✨ Искра — Persona/Space;
- 👏 Аплодисменты — Persona/Space;
- 💐 Букет — Persona;
- 🏮 Фонарик — Space.

В каталоге нет цены. Реальная monetization не моделируется как скрытый numeric field.

## API

Development prefix: `/support/v1`.

План первого checkpoint:

- catalog;
- собственные support settings;
- собственная received history;
- Persona public shelf + send gift;
- Space support settings;
- Space public shelf + send gift;
- manager-only Space received history.

Публичный shelf не должен раскрывать sender/message. Ledger mutation endpoints не создаются.

## Abuse boundary

Первый rate limit реализуется server-side по durable ledger. Поскольку gifts бесплатны и не дают ranking/power, это допустимый alpha baseline. До любых реальных платежей необходимы transactional/fraud controls, idempotent provider events, refunds/chargebacks и отдельная financial threat model.

## UI/UX

- calm «Поддержать» вместо агрессивного donate CTA;
- никаких countdown/limited offer/whale/top donor паттернов;
- shelf вторичен по отношению к Persona/Space content;
- counts не используются как social authority score;
- consent toggle и пояснение последствий должны быть понятными;
- gift picker показывает смысл жеста, а не «ценность».

## Release gate

Перед `0.5.3-alpha.1`:

- additive migration и одна Alembic head;
- support/privacy/block/permission contracts;
- отсутствие financial/power fields в API regression tests;
- SPA production build;
- abuse/privacy/UI review;
- documentation sync;
- functional exact-head CI;
- version bump;
- второй exact-head CI;
- merge только после второго gate.
