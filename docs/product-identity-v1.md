# PubChat Stage 5 — Product Identity & Engagement

Рабочая линия после выпущенного `0.4.0-alpha.1`: `0.5.0-alpha.x`.

## Цель

Сделать PubChat узнаваемым самостоятельным продуктом поверх уже построенного social core. Мы не копируем космическую эстетику Galaxy и не превращаем социальную власть в товар.

## Первый slice

### Persona Appearance

Persona управляет собственным визуальным образом независимо от Account/security:

- accent/theme preset;
- profile background preset;
- avatar frame preset;
- status line.

Appearance — косметический слой. Он не влияет на trust, permissions, moderation или discovery ranking. Публичное чтение appearance выполняется только после той же privacy/block проверки, которая разрешает просмотр Persona-профиля. Если профиль скрыт, appearance не становится обходным каналом утечки.

### Space Appearance

Living Space получает визуальную индивидуальность:

- theme preset;
- cover/background preset;
- ambient icon/emoji;
- short welcome line.

Оформлением управляют только scoped owner/moderator. Оно не меняет membership policy, permissions и discovery rank.

Для Space Discovery используется bounded batch contract до 100 UID. Он возвращает только те Spaces, которые viewer вправе разрешить: public/unlisted или private при ownership/active membership. Недоступные private UID просто не возвращаются. Это сохраняет privacy и убирает HTTP N+1 на карточках discovery.

### Recurring Activities

Activity — социальная надстройка над Living Space для повторных встреч:

- host/creator;
- allowlisted activity type;
- базовый `starts_at` с обязательной explicit timezone;
- recurrence rule `none/daily/weekly/monthly`;
- lightweight participant intent (`going` / `interested`);
- creator или scoped manager может отменить activity.

Activity существует для повторных встреч и разговора, а не для азартной механики.

`recurrence` хранится как компактное правило вместе с базовым `starts_at`. PubChat **не материализует заранее бесконечную серию строк в БД** и не запускает cron, создающий события на годы вперёд. API вычисляет `next_starts_at` при чтении, сохраняя одну canonical запись-шаблон. Все engagement timestamps наружу сериализуются как explicit UTC (`Z`).

RSVP относится к Activity-шаблону и означает устойчивое намерение участвовать в этой активности. Когда позже появятся occurrence-specific attendance/reminders, они будут отдельной сущностью и не изменят текущий контракт задним числом.

Список Activities загружает RSVP counters и viewer RSVP bulk-запросами, без N+1 на каждую карточку.

## SPA / UI

Первый slice включает:

- экран «Стиль образа»;
- privacy-aware appearance в обычном профиле Persona;
- Space appearance в Discovery без влияния на сортировку;
- экран «Жизнь пространства»;
- ближайший occurrence recurring activity;
- RSVP `Интересно` / `Иду`;
- отмену activity creator/manager;
- mobile-first routes и context navigation.

## Инварианты

- Account != Persona.
- Appearance != reputation.
- Cosmetics != permissions.
- Space appearance != discovery power.
- Paid cosmetic content, если появится позже, не даёт moderation/trust/reputation преимуществ.
- Все новые UI surfaces работают mobile-first в SPA и используют существующий UI Kit.
- Backend contracts проектируются reusable для будущих Android/iOS клиентов.

## Не входит в первый slice

- внутренняя валюта;
- платежи;
- creator payouts;
- loot boxes / casino mechanics;
- marketplace;
- transfer/sale of Account, Persona, Space roles or reputation;
- competitive ranking, который можно купить;
- occurrence-specific reminders/attendance history.

## Release gate первого slice

- Stage 5 branch синхронизирован с `main@0.4.0-alpha.1`;
- additive migration only;
- одна Alembic head;
- typed `/appearance/v1` and `/activities/v1` contracts;
- no privileged fields in client-writable DTO;
- privacy/scoped-role enforcement server-side;
- bounded batch appearance contract;
- explicit timezone/UTC API contract;
- contract tests;
- production SPA build;
- mobile Persona/Space customization surfaces;
- final privacy/permissions/migration self-review;
- canonical version bump только после зелёного functional exact-head CI;
- повторный exact-head CI уже на финальной версии перед merge.
