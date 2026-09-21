# Browser compatibility v1

Документ фиксирует browser-level launch gate для PubChat и результат аудита старого дефекта регистрации в Safari.

## Исторический Safari registration defect

В ранней реализации регистрации (commit `45f2d58d`, апрель 2025) frontend получал CSRF cookie при mount страницы, а регистрационный POST зависел от того, что этот cookie будет сохранён и отправлен браузером. Axios был настроен с `withCredentials: true`, при этом API origin мог задаваться отдельно через `VITE_API_BASE_URL`, а fallback указывал на `http://localhost:9000`.

Backend в той версии устанавливал `XSRF-TOKEN` как HttpOnly cookie с `SameSite=Lax`, `secure=False`, а CSRF validator читал только этот cookie. То есть регистрация имела жёсткую зависимость от cookie transport; header/body proof не использовался.

Safari/WebKit давно строже других браузеров относится к third-party/cross-site cookies. Если production frontend и API в той версии оказывались в cross-site контексте, `withCredentials` сам по себе не мог заставить Safari принять/отправить blocked third-party cookie. В результате GET CSRF мог выглядеть успешным, а следующий POST registration — прийти без `XSRF-TOKEN` и быть отклонён.

Есть и второй race-фактор ранней формы: CSRF fetch выполнялся асинхронно в `onMounted`, но submit path не ожидал успешного CSRF handshake непосредственно перед registration. На медленном/особом browser scheduling это позволяло отправить форму раньше готового cookie.

### Уровень уверенности

Это наиболее вероятная корневая причина по сохранённому коду. Точного production origin/cookie trace Safari за 2025 год в repository нет, поэтому исторический инцидент нельзя честно объявить доказанным только исходниками.

## Что изменилось сейчас

Начиная с `0.6.20-alpha.1` browser contract явно same-origin:

- SPA по умолчанию использует `/api`;
- Vite dev/preview proxy отправляет `/api` HTTP и WebSocket traffic в backend;
- legacy fallback `http://localhost:9000` удалён из browser source и запрещён CI guard;
- explicit cross-origin API остаётся только осознанной deployment-конфигурацией, а не fallback.

CSRF теперь использует две связанные части proof:

- signed `XSRF-TOKEN` cookie: `HttpOnly`, `SameSite=Lax`, `Secure` при HTTPS, `Path=/`, bounded lifetime;
- тот же подписанный proof возвращается `/csrf/get` с `Cache-Control: no-store`, хранится SPA только в памяти и отправляется в `X-CSRF-Token` для unsafe requests.

Backend принимает unsafe request только если cookie/header присутствуют, совпадают и signature/expiry валидны. Cookie без header и header без cookie отклоняются. API client сам bootstrap-ит proof перед POST/PUT/PATCH/DELETE, поэтому корректность регистрации/логина больше не зависит от асинхронного `onMounted`.

Refresh после полного reload также получает новый CSRF proof и использует HttpOnly refresh cookie; access token остаётся memory-only и не сохраняется в local/session storage.

## Подтверждение в CI

Playwright browser job поднимает отдельные PostgreSQL/Redis, реальный Uvicorn backend и production-like Vite preview через same-origin `/api`.

Один и тот же journey проходит в:

- Chromium desktop;
- Firefox desktop;
- WebKit / Safari-compatible engine;
- narrow mobile Chromium.

Journey проверяет registration → authenticated shell → full reload/refresh rotation → Messenger route → logout/revocation → login, HttpOnly/SameSite refresh cookie, отсутствие persisted bearer и отсутствие notification permission prompt на bootstrap.

Functional exact-head CI #637 прошёл весь matrix вместе с backend/frontend и production dependency audits.

## Оставшийся security debt

Automated WebKit существенно сильнее API-only теста, но не заменяет Safari на реальном Apple device. До beta остаются iOS/iPadOS installed Home Screen/PWA push rehearsal, upload/media security review, privacy side-channel review и accessibility/device checks.

Нельзя исправлять browser совместимость ослаблением `SameSite`/`Secure` без threat-model review. Если в будущем API снова станет cross-site, auth/CSRF contract должен проектироваться отдельно от текущего same-origin baseline.

## Browser launch matrix

До beta обязательны автоматизированные smoke journeys минимум для:

- Chromium desktop;
- Firefox desktop;
- WebKit/Safari-compatible engine;
- narrow/mobile viewport;
- iOS/iPadOS installed PWA для install/push-specific flows, где доступна device rehearsal.

Критические journeys:

1. registration → authenticated session bootstrap;
2. login → refresh rotation → reload;
3. logout/revocation;
4. Space load + members + realtime room socket;
5. Messenger load + direct message + reconnect;
6. attachment upload;
7. PWA service-worker update without auth/private cache leakage;
8. notification permission/subscription only after explicit user action.

## CI contract

Playwright browser smoke является отдельным обязательным gate. Network trace и video выключены, чтобы CI artifacts не становились новым местом хранения auth/private data; при падении сохраняется только screenshot.

Production dependency security также является gate: frontend проверяется `npm audit --omit=dev --audit-level=high`, backend — pinned `pip-audit`. Известные production vulnerabilities не маскируются allow-list исключениями в этом checkpoint.
