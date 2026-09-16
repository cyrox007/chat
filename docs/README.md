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
- [`revival-roadmap.md`](revival-roadmap.md) — исторический revival-plan.
- [`../CHANGELOG.md`](../CHANGELOG.md) — история выпущенных версий.
- [`versioning.md`](versioning.md) — политика alpha/beta/stable.
- [`versioning-quick-reference.md`](versioning-quick-reference.md) — краткий статус версии.
- [`ui-ux-kit.md`](ui-ux-kit.md) — основная дизайн-система и UX-правила.
- [`ui-ux-notifications.md`](ui-ux-notifications.md) — notification/reminder UX extension.
- [`ui-ux-discovery.md`](ui-ux-discovery.md) — explainable organic discovery UX rules.
- [`ui-ux-pwa.md`](ui-ux-pwa.md) — install/update/offline UX extension.

## Для разработчика

- [`architecture.md`](architecture.md) — модули, домены, данные и границы ответственности.
- [`client-architecture.md`](client-architecture.md) — SPA-first/API-first модель клиента.
- [`api-and-realtime.md`](api-and-realtime.md) — HTTP API, auth/session и WebSocket v2.
- [`security-and-privacy.md`](security-and-privacy.md) — security model, privacy boundaries и review checklist.
- [`development.md`](development.md) — ветки, миграции, тесты и CI.
- [`operations.md`](operations.md) — production-конфигурация, reminder worker и эксплуатационные ограничения.
- [`prebeta-hardening-v1.md`](prebeta-hardening-v1.md) — Stage 6 PostgreSQL/migration integration baseline, выпущенный в `0.6.0-alpha.1`.
- [`release-checklist.md`](release-checklist.md) — release gate.

## Доменные документы

- [`identity-v2.md`](identity-v2.md) — Account/Persona/Credential/Session/Privacy.
- [`realtime-v2.md`](realtime-v2.md) — tickets, Redis pub/sub, presence, reconnect.
- [`product-identity-v1.md`](product-identity-v1.md) — Persona/Space appearance и recurring Activities.
- [`social-engagement-v2.md`](social-engagement-v2.md) — earned achievements и Conversation Rounds.
- [`activity-occurrences-v1.md`](activity-occurrences-v1.md) — Activity Occurrences, reminders и notification inbox, выпущенные в `0.5.2-alpha.1`.
- [`creator-support-v1.md`](creator-support-v1.md) — opt-in gifts, append-only ledger и cosmetic entitlements, выпущенные в `0.5.3-alpha.1` без real-money flows.
- [`discovery-v1.md`](discovery-v1.md) — eligibility-first, explainable organic Space discovery, выпущенный в `0.5.4-alpha.1`.
- [`web-application-maturity-v1.md`](web-application-maturity-v1.md) — PWA shell, безопасный offline contract, notification lifecycle и внешний reminder worker, выпущенные в `0.5.5-alpha.1`.

## Статус документов

`VERSION` и `CHANGELOG.md` — источник истины для выпущенного checkpoint. Активный development scope находится в `roadmap.md` и профильных документах следующего slice.

Текущий release: `0.6.0-alpha.1`.

Текущая development-линия: `0.6.0-alpha.x` — Pre-beta hardening продолжается.
