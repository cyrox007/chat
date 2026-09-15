# PubChat Stage 5.5 — Explainable Organic Discovery

Released in: `0.5.4-alpha.1`.

## Цель

Сделать поиск Living Spaces полезнее без превращения discovery в непрозрачный рейтинг и без возможности купить органическую видимость.

Endpoint `/discovery/v1/spaces` существует отдельно от стабильного каталога `/spaces/v1`: каталог остаётся предсказуемым filter/list API, а персонализированная выдача развивается независимо.

## Главный принцип

**Eligibility раньше ranking.** Сначала backend определяет, какие Spaces вообще допустимо показать конкретному Account. Только после этого допустимый набор сортируется.

Ranking никогда не должен делать private/inactive/blocked ресурс видимым.

## Organic signals v1

Первый алгоритм использует только bounded социальный контекст:

- несколько разных недавних авторов в Space;
- ближайшая scheduled Activity/Event;
- общие темы/tags с уже активными Spaces пользователя;
- знакомый purpose;
- explicit `social_intent` Persona;
- небольшой freshness signal;
- небольшой capped member-count signal;
- существующее membership/pending state как слабый контекст.

Недавняя активность считается по **разным авторам**, а не по числу сообщений, чтобы один Account не мог поднять Space спамом.

## Что намеренно НЕ используется

Алгоритм не импортирует и не использует:

- legacy `Room.rating`;
- gift/support counts;
- price/currency/payment;
- paid boost;
- moderation authority;
- achievement score;
- скрытый «рейтинг человека».

Support/gifts остаются социальным жестом и никогда автоматически не становятся discovery power.

## Privacy и block

- canonical Space visibility/membership policy применяется до ranking;
- Account-level block подавляет новую owner-led публичную рекомендацию;
- existing active/pending membership не удаляется автоматически из-за block — это отдельное community relation;
- private/unlisted Space без active membership не раскрывает через discovery внутреннее название/время ближайшей Activity/Event;
- query/purpose/tag filters только сужают уже допустимый набор и не расширяют visibility.

## Explainability

Клиент не получает числовой score. Projection содержит только:

- `algorithm` — идентификатор версии алгоритма;
- до трёх `reasons` с стабильными кодами и UX-label;
- `upcoming` только если этот контекст разрешено раскрывать.

Примеры причин:

- «Здесь недавно общались»;
- «Скоро общая активность»;
- «Похожие темы на ваши пространства»;
- «Подходит вашему текущему настрою»;
- «Новое пространство».

Score остаётся server-only implementation detail и не является публичным API contract.

## Bounded work

Первая версия ranking работает на bounded candidate pool до 200 Spaces. Это защищает latency и БД от unbounded personalized scan.

После score применяется небольшой diversity pass: когда подряд идут слишком похожие purpose, близкий по score кандидат другого формата может подняться выше. Diversity не обходит eligibility.

### Известное alpha-ограничение

Candidate pool organic-v1 начинается с canonical catalog, отсортированного по новизне. Поэтому очень старый Space за пределами первых 200 кандидатов может не попасть в персонализированный ranking даже после новой активности.

До beta candidate generation должен собираться из нескольких bounded источников — recent activity, upcoming events/activities, shared context и freshness — без unbounded scan.

## SPA

Основной Space Discovery screen использует `/discovery/v1/spaces`.

Карточка показывает:

- обычные Space metadata;
- appearance;
- до трёх chips «Почему здесь»;
- ближайшую доступную Activity/Event;
- привычное join/open действие.

Не показываются «очки релевантности», leaderboard или paid badge.

## Quality gate `0.5.4-alpha.1`

Перед release пройдены:

- backend import/contracts;
- frontend production build;
- privacy/block/query review;
- regression против paid/gift/legacy rating signals;
- docs/UI contract sync;
- functional exact-head CI;
- version bump;
- обязательный второй exact-head CI перед merge.
