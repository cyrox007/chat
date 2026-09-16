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

Текущий SPA по умолчанию использует same-origin `/api`, а production reverse proxy обслуживает frontend/API под одним сайтом. Это убирает главный cross-site-cookie риск ранней схемы.

Текущий CSRF cookie:

- `HttpOnly`;
- `SameSite=Lax`;
- `Secure` при HTTPS-конфигурации;
- `Path=/`;
- имеет bounded lifetime.

Регистрация v2 и refresh session должны проверяться в реальном WebKit browser, а не только unit/API tests.

## Оставшийся security debt

Текущий CSRF validator по-прежнему валидирует подписанный cookie сам по себе. Это не classic double-submit token с независимым header proof. В Stage 6.5 требуется отдельный CSRF/session review: выбранная модель должна быть явно задокументирована, а не случайно зависеть от browser cookie defaults.

Нельзя исправлять Safari совместимость ослаблением `SameSite`/`Secure` без threat-model review. Если в будущем API снова станет cross-site, auth/CSRF contract должен быть спроектирован явно, а не обходиться browser exceptions.

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

## CI direction

Добавить Playwright browser smoke suite отдельным gate. Для Safari regression нужен WebKit project, который выполняет настоящую регистрацию через production-like same-origin proxy и проверяет cookie/session flow. API-only test не считается достаточным для этого класса дефекта.

Browser smoke должен сохранять network trace/logs при падении, но не артефакты с access/refresh token values или приватным message content.
