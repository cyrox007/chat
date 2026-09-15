# Документация PubChat

Этот каталог — единая точка входа в документацию проекта. Документы разделены по назначению: продукт, пользовательские сценарии, установка, архитектура, разработка и эксплуатация.

## Начать работу

1. [`system-requirements.md`](system-requirements.md) — что требуется для запуска.
2. [`installation.md`](installation.md) — установка backend/frontend и первый старт.
3. [`user-guide.md`](user-guide.md) — что умеет PubChat и как пользоваться функциями.
4. [`troubleshooting.md`](troubleshooting.md) — типовые проблемы.

## О продукте

- [`product-concept.md`](product-concept.md) — позиционирование и продуктовые инварианты.
- [`roadmap.md`](roadmap.md) — актуальная дорожная карта.
- [`revival-roadmap.md`](revival-roadmap.md) — совместимая историческая ссылка на новый roadmap.
- [`../CHANGELOG.md`](../CHANGELOG.md) — история выпущенных версий.
- [`versioning.md`](versioning.md) — политика alpha/beta/stable.
- [`versioning-quick-reference.md`](versioning-quick-reference.md) — краткий статус версии.
- [`ui-ux-kit.md`](ui-ux-kit.md) — дизайн-система и UX-правила.

## Для разработчика

- [`architecture.md`](architecture.md) — модули, домены, данные и границы ответственности.
- [`client-architecture.md`](client-architecture.md) — SPA-first/API-first модель клиента.
- [`api-and-realtime.md`](api-and-realtime.md) — HTTP API, auth/session и WebSocket v2.
- [`development.md`](development.md) — ветки, миграции, тесты и CI.
- [`operations.md`](operations.md) — production-конфигурация и эксплуатационные ограничения.
- [`release-checklist.md`](release-checklist.md) — release gate.

## Доменные документы

- [`identity-v2.md`](identity-v2.md) — Account/Persona/Credential/Session/Privacy.
- [`realtime-v2.md`](realtime-v2.md) — tickets, Redis pub/sub, presence, reconnect.
- [`product-identity-v1.md`](product-identity-v1.md) — Persona/Space appearance и recurring Activities.
- [`social-engagement-v2.md`](social-engagement-v2.md) — earned achievements и Conversation Rounds.
- [`activity-occurrences-v1.md`](activity-occurrences-v1.md) — development-дизайн occurrences/reminders/inbox для `0.5.2-alpha.x`.

## Статус документов

`VERSION` и `CHANGELOG.md` — источник истины для выпущенного checkpoint. Активный development scope находится в `roadmap.md` и domain-документе ветки.

Текущий release: `0.5.1-alpha.1`.

Активная development-линия: `0.5.2-alpha.0`.
