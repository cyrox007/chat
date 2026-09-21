# Установка и первый запуск PubChat

Документ описывает текущий manual development setup. Готового Docker Compose/deployment bundle в репозитории пока нет.

## 1. Подготовьте инфраструктуру

Нужны:

- Python 3.12;
- Node.js 20 + npm;
- PostgreSQL;
- Redis;
- Git.

Проверенный baseline подробно описан в [`system-requirements.md`](system-requirements.md).

## 2. Получите проект

```bash
git clone https://github.com/cyrox007/chat.git
cd chat
```

Для обычного использования берите `main`. Активные `revival/*` ветки могут содержать незавершённые alpha-функции.

## 3. PostgreSQL

Создайте отдельную базу и пользователя либо используйте существующий development PostgreSQL. Значения должны совпадать с `backend/.env`.

Пример для локальной среды:

```sql
CREATE DATABASE chat;
CREATE USER pubchat WITH PASSWORD 'change-me';
GRANT ALL PRIVILEGES ON DATABASE chat TO pubchat;
```

При современных PostgreSQL могут дополнительно понадобиться права на schema `public`, в зависимости от политики вашей установки.

## 4. Redis

Запустите Redis и убедитесь, что backend может подключиться по URL вида:

```text
redis://localhost:6379/0
```

В production Redis обязателен. Development fallback при `DEBUG=True` не является multi-worker replacement.

## 5. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Для PowerShell/Windows используйте WSL2 как рекомендуемую development-среду. CI проекта работает на Linux, а requirements включают `uvloop`.

### Настройте `.env`

Минимально проверьте:

```dotenv
DEBUG=True
FRONTEND_URL=http://localhost:5173
SERVER_HTTP_PROTOCOL=http://
SERVER_ADDR=localhost
SERVER_PORT=9000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chat
DB_USER=pubchat
DB_PASSWORD=change-me
REDIS_URL=redis://localhost:6379/0
```

Обязательно задайте **три разные** случайные строки длиной не менее 32 символов:

```dotenv
JWT_ACCESS_SECRET_KEY=...
JWT_REFRESH_SECRET_KEY=...
CSRF_SECRET_KEY=...
```

Backend специально не имеет production-capable default secrets и откажется работать при слабой конфигурации в security-sensitive path.

### Примените migrations

Из каталога `backend`:

```bash
alembic heads
alembic upgrade head
```

`alembic heads` должен показывать одну head revision.

### Запустите backend

Development helper:

```bash
python run_server.py
```

Либо напрямую:

```bash
uvicorn app:app --host 0.0.0.0 --port 9000 --reload
```

Проверка:

```text
http://localhost:9000/health
http://localhost:9000/service/version
http://localhost:9000/docs
```

`/docs` — встроенная FastAPI/OpenAPI документация.

## 6. Frontend

Откройте второй терминал:

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

По умолчанию менять `frontend/.env.local` не требуется. Browser contract использует same-origin `/api`, а Vite сам проксирует его в backend `http://127.0.0.1:9000`.

При нестандартном backend development address задайте только target proxy перед запуском Vite:

```bash
PUBCHAT_DEV_BACKEND=http://127.0.0.1:9000 npm run dev
```

`VITE_API_BASE_URL=/api` и пустой `VITE_API_WS_SERVER_URL` уже находятся в `.env.example`. Не возвращайте `http://localhost:9000` как browser fallback: это снова сделает cookie/session flow cross-origin.

Откройте URL, который напечатает Vite; стандартно это `http://localhost:5173`.

## 7. Первый сценарий проверки

После старта:

1. Откройте регистрацию.
2. Создайте Account/Persona.
3. Убедитесь, что после регистрации открывается SPA shell.
4. Создайте или откройте Space.
5. Проверьте realtime connection state.
6. Отправьте сообщение.
7. Откройте профиль и privacy settings.
8. Создайте Activity в «Жизни пространства» и поставьте RSVP.

В development-линии `0.5.2-alpha.x` также доступны opt-in reminders и личный notification inbox; эти функции не считаются released, пока соответствующий PR не слит в `main`.

## 8. Production build frontend

```bash
cd frontend
npm ci
npm run build
```

Результат создаётся Vite в `dist/`. `frontend/nginx.conf` содержит базовую SPA-конфигурацию, однако production reverse proxy должен дополнительно корректно проксировать API/WebSocket и использовать TLS.

## 9. Обновление существующей установки

Для production-oriented установки основной entrypoint из корня проекта:

```bash
./update.sh
```

Он делегирует в `ops/deploy.sh`: обновляет `main`, зависимости, Alembic migrations, staged frontend build и rolling backend reload с readiness gate. Перед значимым alpha-обновлением всё равно сделайте backup PostgreSQL/uploads.

Перед обновлением:

1. Сделайте backup PostgreSQL и uploads.
2. Получите нужный release/main commit.
3. Установите обновлённые Python/npm dependencies.
4. Выполните `alembic heads` и убедитесь, что head одна.
5. Выполните `alembic upgrade head`.
6. Соберите frontend заново.
7. Перезапустите backend workers.
8. Проверьте `/health`, `/service/version`, login/refresh и WebSocket connection.

На alpha-стадии нельзя выполнять production migration без backup и rehearsal на копии данных.

## 10. Тесты перед отправкой изменений

Backend:

```bash
cd backend
python -m compileall -q .
python -c "from app import app; assert app.title == 'PubChat API'"
alembic heads
python -m unittest discover -s tests -p 'test_*.py'
```

Frontend:

```bash
cd frontend
npm ci
npm run build
npm audit --omit=dev --audit-level=high
```

Для локального повторения browser launch gate дополнительно установите pinned Playwright без изменения lockfile и browser engines:

```bash
npm install --no-save --package-lock=false @playwright/test@1.55.0
npx playwright install chromium firefox webkit
npx playwright test --config=playwright.config.mjs
```

Browser test ожидает доступные PostgreSQL/Redis/backend и production-like frontend stack; CI поднимает этот контур автоматически. Backend production dependencies отдельно проверяются `pip-audit`.

Те же основные проверки выполняет GitHub Actions.
