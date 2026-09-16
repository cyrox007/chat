# PubChat UI/UX — PWA & Offline Extension

Этот документ дополняет основной `ui-ux-kit.md` для Stage 5.6.

## Принцип

PWA-функции должны ощущаться как спокойное расширение приложения, а не как агрессивный «установи сейчас» маркетинговый слой.

## Install prompt

Показывается только когда сам браузер предоставляет `beforeinstallprompt`.

Правила:

- не перекрывает основной контент модальным окном;
- не показывается в standalone mode;
- имеет два равноправных действия: «Установить» и «Не сейчас»;
- dismiss действует в пределах browser session;
- mobile placement не перекрывает bottom navigation;
- prompt имеет accessible region + heading.

Нельзя использовать countdown, urgency, nagging loop или скрывать кнопку отказа.

## Update notice

При готовом обновлении показывается компактный status banner.

- текст объясняет, что reload применит новую версию;
- пользователь сам запускает reload;
- notice можно скрыть;
- используется polite live region;
- dismiss control имеет keyboard-visible focus.

Обновление не должно внезапно перезагружать страницу во время разговора/редактирования.

## Offline state

Offline banner объясняет только фактическое состояние:

- открытый интерфейс остаётся доступным;
- realtime/API действия временно недоступны;
- соединение восстановится при возвращении сети.

Нельзя обещать «всё сохранено офлайн», если приватные API/messages не кэшируются.

## Cache privacy

UI/UX copy не должно создавать впечатление, что PubChat хранит приватные разговоры в PWA cache.

Service worker предназначен для shell/static assets. Messages, inbox, profile/private projections и auth state остаются network/server state.

## Accessibility

- новые notices не крадут focus автоматически;
- status changes используют `aria-live="polite"`;
- icon-only controls имеют aria-label;
- все действия доступны с клавиатуры;
- `prefers-reduced-motion` должен уважаться общими motion rules;
- prompt/banner не должны блокировать основной route content.

## Mobile

PWA controls не добавляют пятый пункт в bottom navigation. Bottom navigation остаётся навигацией продукта, а install/update — временным app-shell state.

## Native future

PWA install prompt и browser-specific events остаются frontend adapter logic. Product/domain API не должен зависеть от `beforeinstallprompt`, Service Worker или других browser-only primitives — это сохраняет возможность Android/iOS клиента.
