# PubChat Stage 5.5 — Explainable Organic Discovery

Released in: `0.5.4-alpha.1`; candidate-generation hardening: `0.6.24-alpha.1`.

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

Ranking работает на общем candidate pool до 200 Spaces. Это защищает latency и БД от unbounded personalized scan.

Начиная с `organic-v2` (`0.6.24-alpha.1`) default discovery собирает этот pool из нескольких независимых bounded источников:

- active/pending memberships пользователя;
- recent activity по distinct authors;
- ближайшие scheduled Events и materialized Activity occurrences;
- shared tags и purpose из уже знакомых Spaces;
- newest active Spaces как freshness fallback.

Каждый источник имеет собственный cap, затем источники interleave-ятся round-robin с dedupe. Поэтому freshness не может вытеснить весь recent/upcoming/shared context, а старый Space может снова попасть в выдачу после новой активности.

Candidate generation не является eligibility: собранные UID обязательно проходят canonical Space visibility/membership policy до ranking/projection.

Явный search/purpose/tag mode сохраняет canonical catalog filtering semantics и не использует personalized source mixing.

После score применяется небольшой diversity pass: когда подряд идут слишком похожие purpose, близкий по score кандидат другого формата может подняться выше. Diversity не обходит eligibility.

## Large-pool privacy regression

`0.6.26-alpha.1` закрепляет privacy/block semantics на candidate set, который превышает общий discovery pool cap.

- block suppresses новую owner-led public recommendation, но не стирает уже существующую active/pending community relation;
- private Space без membership не проходит canonical eligibility даже если activity/event source внутренне выбрал его как candidate;
- pending membership в private Space не даёт права на recent-conversation/upcoming live context;
- privacy regression одновременно проверяет отсутствие sensitive sentinel data в serialized response и сохранение bounded query budget.

## Performance contract

`0.6.25-alpha.1` добавляет отдельный query/latency guard для discovery.

- основной CI budget измеряется по количеству реальных SQL round-trips, а не по хрупкому локальному таймингу;
- default `organic-v2` path должен оставаться bounded и не превращаться в N+1 при росте candidate set;
- explicit filter path измеряется отдельно;
- operational profiler возвращает только aggregate counts/timing и не выводит identifiers, SQL parameters или result payload;
- подробности и CLI: [`discovery-performance-v1.md`](discovery-performance-v1.md).

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
