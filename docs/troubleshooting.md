# PubChat — диагностика проблем

## Backend не запускается: secrets must be configured

Проверьте `backend/.env`.

Нужны три разные строки длиной минимум 32 символа:

- `JWT_ACCESS_SECRET_KEY`;
- `JWT_REFRESH_SECRET_KEY`;
- `CSRF_SECRET_KEY`.

Значения из `.env.example` нельзя использовать в production.

## Backend не подключается к PostgreSQL

Проверьте:

- `DB_HOST`;
- `DB_PORT`;
- `DB_NAME`;
- `DB_USER`;
- `DB_PASSWORD`;
- доступность PostgreSQL из среды backend;
- права пользователя на database/schema.

Быстрая проверка приложения: `/health`.

## Alembic показывает больше одной head

Не применяйте migrations вслепую. Сначала найдите разошедшиеся revision branches и исправьте migration graph/merge revision. CI проекта требует ровно одну head.

## Redis недоступен

В production это блокирующая проблема для корректного distributed realtime. Проверьте `REDIS_URL`, сеть и сам Redis.

В DEBUG некоторые realtime operations могут использовать development fallback, но он не предназначен для multi-worker production.

## SPA не видит backend

Проверьте `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://localhost:9000
```

После изменения Vite env перезапустите `npm run dev`.

Также проверьте, что backend `FRONTEND_URL` содержит origin SPA, например `http://localhost:5173`.

## WebSocket не соединяется

Проверьте:

- backend доступен;
- Redis работает;
- HTTP login/session работает;
- ticket endpoint доступен;
- reverse proxy поддерживает WebSocket upgrade;
- `VITE_API_WS_SERVER_URL` корректен, если задан вручную.

WebSocket URL не должен содержать JWT/token. Realtime v2 получает одноразовый ticket по HTTP и передаёт его первым frame.

## После reload пользователь вышел из аккаунта

Access token намеренно не хранится в localStorage. После reload SPA должна восстановить access session через HttpOnly refresh cookie.

Проверьте:

- cookie присутствует и не блокируется браузером;
- origin/CORS соответствуют конфигурации;
- в production используется HTTPS;
- refresh session не истекла/не отозвана;
- CSRF flow доступен.

## 403 после запроса

`403` в PubChat обычно означает authorization decision, а не expired session. Не пытайтесь чинить его бесконечным refresh/reconnect.

Проверьте membership, scoped role, privacy, block или состояние ресурса.

## 404 на существующий профиль/Space

Для privacy-sensitive объектов `404` может быть намеренным, чтобы не раскрывать существование объекта, к которому viewer не имеет доступа.

## Realtime постоянно reconnecting

Проверьте:

- membership действительно active;
- Space не restricted;
- Redis connection;
- heartbeat interval/TTL configuration;
- browser network;
- proxy idle timeout;
- backend logs без раскрытия credential material.

## Сообщения дублируются после reconnect

Новый message flow должен использовать `frontId` и server-side idempotency. Если duplicate появился, проверяйте не только SPA dedupe, но и Redis/idempotency claim + database write flow.

## Участник виден offline при открытом приложении

Проверяйте Redis presence keys и heartbeat. Heartbeat должен продлевать TTL connection record и user/Space presence indexes.

## Frontend build падает

```bash
cd frontend
rm -rf node_modules
npm ci
npm run build
```

Не удаляйте `package-lock.json` без причины. CI использует Node 20 и `npm ci`.

## Python dependency install падает на Windows

Backend baseline проверяется на Linux/Python 3.12, а requirements включают `uvloop`. Для Windows рекомендуется WSL2.

## Upload открывается на одном backend instance, но не на другом

Текущий `/uploads` использует локальный filesystem. Для multi-instance production требуется shared/object storage.

## Уведомления не появляются — In development

В `0.5.2-alpha.x` напоминания opt-in и сначала работают как in-app sync, а не browser/native push.

Проверьте:

- reminder включён;
- Account остаётся активным участником Space;
- occurrence попадает в materialization horizon;
- вызывается `/notifications/v1/sync`;
- notification ещё не была создана ранее для того же occurrence.

## Версия frontend/backend не совпадает

Проверьте root `VERSION`, пересоберите frontend и перезапустите backend. Backend version доступна через `/service/version`; frontend получает номер во время Vite build.

## Когда заводить issue

Если проблема воспроизводится после проверки конфигурации, приложите:

- точную версию PubChat;
- branch/commit;
- ОС;
- Python/Node versions;
- шаги воспроизведения;
- ожидаемое/фактическое поведение;
- sanitized logs без токенов, cookies и secrets.
