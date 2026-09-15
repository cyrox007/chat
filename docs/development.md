# Разработка PubChat

## Процесс

Работа ведётся в отдельных ветках от актуального `main`. Для каждого законченного slice создаётся pull request. Сначала проверяется функциональный head, затем обновляются `VERSION` и `CHANGELOG.md`, после чего CI запускается повторно уже на versioned head. Merge выполняется только после второго успешного gate.

## Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Проверки:

```bash
python -m compileall -q .
python -c "from app import app; assert app.title == 'PubChat API'"
alembic heads
python -m unittest discover -s tests -p 'test_*.py'
```

Alembic должен иметь одну head. Новые schema changes оформляются отдельными migrations; предпочтительны additive и data-preserving изменения.

## Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Release/build check:

```bash
npm ci
npm run build
```

## Правила реализации

- Backend остаётся authoritative для permissions и privacy.
- ORM model не является API contract.
- Новые request payload описываются typed DTO.
- Public/private response projections собираются явно.
- Для конкурентных инвариантов используются DB constraints/indexes.
- Новая пользовательская функция выпускается вместе с mobile/loading/empty/error/permission состояниями.
- Legacy домены мигрируют постепенно через versioned contract и compatibility bridge, а не big-bang rewrite.

## PR

Описание PR должно фиксировать development line, реализованные contracts, migrations, UI/UX scope, известный долг и status CI.

Подробнее: `installation.md`, `architecture.md`, `ui-ux-kit.md`, `release-checklist.md`.
