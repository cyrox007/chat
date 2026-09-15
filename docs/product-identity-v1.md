# PubChat Stage 5 — Product Identity & Engagement

Рабочая линия после `0.4.0-alpha.1`: `0.5.0-alpha.x`.

## Цель

Сделать PubChat узнаваемым самостоятельным продуктом поверх уже построенного social core. Мы не копируем космическую эстетику Galaxy и не превращаем социальную власть в товар.

## Первый slice

### Persona Appearance

Persona может управлять собственным визуальным образом независимо от Account/security:

- accent/theme preset;
- profile background preset;
- avatar frame preset;
- status line;
- optional compact visual badges.

Appearance — косметический слой. Он не влияет на trust, permissions, moderation или discovery ranking.

### Space Appearance

Living Space получает визуальную индивидуальность:

- theme preset;
- cover/background preset;
- ambient icon/emoji;
- short welcome line.

Оформлением управляют только scoped owner/moderator согласно отдельным permissions. Оно не меняет membership policy и не повышает discovery rank за деньги.

### Recurring Activities

События Stage 4 получают социальный надстройку — Activity:

- recurring schedule;
- host/creator;
- activity type;
- lightweight participant intent (`going` / `interested`);
- optional template for future social-first games.

Activity существует для повторных встреч и разговора, а не для азартной механики.

## Инварианты

- Account != Persona.
- Appearance != reputation.
- Cosmetics != permissions.
- Space appearance != discovery power.
- Paid cosmetic content, если появится позже, не даёт moderation/trust/reputation преимуществ.
- Все новые UI surfaces должны работать mobile-first в SPA и использовать существующий UI Kit.
- Backend contracts проектируются reusable для будущих Android/iOS клиентов.

## Не входит в первый slice

- внутренняя валюта;
- платежи;
- creator payouts;
- loot boxes / casino mechanics;
- marketplace;
- transfer/sale of Account, Persona, Space roles or reputation;
- competitive ranking, который можно купить.

## Release gate первого slice

- additive migrations only;
- typed `/appearance/v1` and `/activities/v1` contracts;
- no privileged fields in client-writable DTO;
- privacy/scoped-role enforcement server-side;
- contract tests;
- production SPA build;
- mobile Persona/Space customization surfaces;
- no Stage 5 merge until Stage 4 is released and Stage 5 rebased/synchronized with `main`.
