# PubChat UI/UX Kit

## Назначение

PubChat должен ощущаться не как «сайт знакомств», не как игровой интерфейс из 2010-х и не как очередной Discord-клон. Интерфейс должен поддерживать продуктовую идею **места отдыха и свободного общения**: спокойный, тёплый, понятный, быстрый, социальный и ненавязчивый.

UI Kit развивается параллельно с backend и доменной моделью. Новая сущность считается завершённой только тогда, когда для неё определены пользовательские состояния, responsive-поведение, accessibility и понятные empty/error/loading сценарии.

## Дизайн-принципы

### 1. Conversation first

Основное действие пользователя — увидеть людей, понять контекст и начать разговор. Интерфейс не должен заставлять проходить через лишние панели, карточки и декоративные экраны прежде, чем пользователь доберётся до общения.

### 2. Calm hospitality

PubChat — место отдыха. Базовая палитра строится на тёплых нейтральных поверхностях и спокойном сливовом акценте. Мы избегаем кислотных цветов, неоновой «космической» стилистики и постоянных ярких уведомлений.

### 3. Context over chrome

Экран должен показывать содержание пространства, людей и событий, а не тяжёлые рамки интерфейса. Навигация и инструменты остаются заметными, но визуально вторичными.

### 4. Progressive disclosure

Редкие и административные функции не конкурируют с ежедневными действиями. Основные действия находятся на виду; сложные настройки, moderation и advanced controls раскрываются по мере необходимости.

### 5. Familiar but not generic

Используем привычные паттерны: нижняя навигация на мобильном, sidebar на широком экране, понятные dialogs/sheets, явные buttons и status chips. Уникальность PubChat создаётся Living Spaces, Persona, social intent и community history, а не нестандартными ради нестандартности контролами.

### 6. Accessible by default

- keyboard navigation;
- `:focus-visible`;
- semantic HTML;
- достаточный contrast;
- touch target примерно 44–48 px;
- `aria-live` для системных состояний;
- reduced motion;
- информация не передаётся только цветом.

## Базовые токены

Новые компоненты используют семантические `--ui-*` переменные из `frontend/src/assets/main.css`.

Группы токенов:

- typography;
- spacing;
- radii;
- background/surface;
- text hierarchy;
- borders;
- primary brand;
- success/warning/danger/info;
- focus;
- elevation;
- motion;
- control heights.

Legacy variables временно остаются aliases. Это позволяет переносить старый интерфейс постепенно, без одномоментного rewrite всего frontend.

## Плотность интерфейса

PubChat должен поддерживать два естественных сценария:

- **Comfortable** — default, просторнее, лучше для телефона и casual общения;
- **Compact** — больше сообщений и участников на экране, полезно активным пользователям и desktop.

Density не должна менять информационную архитектуру — только размеры вертикальных отступов, высоту строк и вторичных контролов.

## Основные компоненты

### Navigation

- App shell;
- desktop sidebar;
- mobile bottom navigation;
- contextual top bar;
- breadcrumbs только в административных/глубоких настройках;
- command/search entry для быстрого перехода между Spaces, Persona и диалогами.

### Identity

- `PersonaAvatar`;
- `PersonaName`;
- `IntentBadge`;
- trust/verification indicators без «рейтинга человека»;
- Persona switcher;
- Profile summary;
- privacy-aware contact actions.

В публичном интерфейсе Account никогда не должен визуально подменять Persona.

### Spaces

- `SpaceCard` — discovery;
- `SpaceHeader` — контекст пространства;
- `SpacePresence` — кто здесь сейчас;
- `SpaceActivity` — событие/активность;
- `SpaceHistory` — память сообщества;
- `SpaceRoleBadge` — scoped роль;
- `SpaceRules`;
- `SpaceEventCard`.

Карточка пространства должна отвечать минимум на четыре вопроса: **что это, кто здесь, что происходит сейчас, зачем мне войти**.

### Engagement

Engagement-поверхности должны усиливать разговор, а не создавать мета-игру вокруг статуса.

#### Achievement shelf

- максимум несколько earned marks на обычном Persona profile;
- название + короткое объяснение + спокойная иконка;
- никакого общего score, уровня, league или позиции;
- отсутствие achievement не выглядит как «плохой профиль»;
- собственная подробная история может показывать личный context, публичный shelf — никогда;
- achievement не используется как verification/trust indicator.

#### Conversation Round

- живёт **внутри `SpaceActivity`**, а не отдельной игровой лобби-страницей;
- один явный prompt;
- `icebreaker`, `choice` и `story_chain` используют общий визуальный каркас;
- `choice` показывает распределение ответов, но не победителя;
- текстовые ответы показывают Persona и контекст участия;
- закрытие раунда выглядит как завершение разговора, не «конец матча»;
- запрещены confetti/jackpot/streak/leaderboard визуальные паттерны по умолчанию;
- blocked Accounts не должны визуально появляться друг у друга через round surface.

#### Support shelf & gift picker

Creator support является вторичной социальной поверхностью, а не магазином.

- публичный shelf показывает только icon/name/count;
- counts не сортируют людей/Spaces и визуально не превращаются в «уровень популярности»;
- sender/message никогда не появляются в публичном shelf;
- собственная/manager received history визуально отделена от публичного профиля;
- CTA — спокойный «Поддержать», без urgency/limited offer/countdown;
- gift picker показывает смысл gesture, а не денежную «ценность»;
- support opt-in объясняет, что функция не влияет на trust/permissions/discovery;
- нет donor leaderboard, top supporter, streak, jackpot, confetti или whale-pattern;
- нет wallet/balance/currency UI;
- Space support живёт на контекстной странице и не получает отдельный пункт mobile bottom navigation;
- support failure не ломает базовый Persona/Space surface.

#### Activity + Round hierarchy

Порядок визуального веса:

1. Activity title/time/context;
2. RSVP и живое участие;
3. Conversation Round как раскрываемая надстройка;
4. achievement как последующая тихая отметка истории.

Achievement не должен прерывать разговор modal-окном. Если позже появится toast о новой отметке, он должен быть dismissible и вторичным.

### Messaging

- message row/bubble;
- reply context;
- reactions;
- attachments;
- composer;
- typing/presence;
- reconnect/offline state;
- delivery state;
- unread separator.

Bubble не должна становиться главным визуальным элементом. Приоритет — читаемость непрерывного разговора.

### Social intent

Intent должен быть компактным, понятным и управляемым прямо из основных экранов.

Примеры пользовательских состояний:

- «Хочу пообщаться»;
- «Открыт новым знакомствам»;
- «Ищу компанию для игры»;
- «Только знакомые»;
- «Не беспокоить».

Формулировки являются UX-копирайтом, а не названиями enum в API.

### Feedback

Единые паттерны:

- toast — короткий результат действия;
- inline notice — ошибка конкретного блока;
- banner — системное состояние;
- empty state — что произошло и что можно сделать дальше;
- skeleton — загрузка структуры;
- progress — только когда есть реальный измеримый процесс.

Ошибка не должна выглядеть как авария всей системы, если сломана одна функция.

### Moderation & safety

Никакой игровой или тюремной визуальной метафоры.

Moderation surface показывает:

- что ограничено;
- почему;
- каким правилом;
- кем/какой системой принято решение;
- срок;
- доступна ли апелляция.

Опасные действия используют confirmation с ясным последствием, а не абстрактное «Вы уверены?».

Engagement/support не создаёт отдельную moderation-систему: жалобы, ограничения, block и appeals продолжают использовать общий Safety/Moderation домен.

## Responsive model

### Mobile

Главная платформа UX. Один основной контекст на экран. Вторичные панели открываются bottom sheet/full-screen panel. Composer всегда остаётся доступным и не прыгает при появлении клавиатуры.

Conversation Round на narrow viewport разворачивается внутри Activity в одну колонку; choice options становятся полноширинными touch targets, а список ответов остаётся вторичным раскрываемым блоком.

Gift picker на narrow viewport использует 1–2 колонки и полноширинный submit; Space support остаётся contextual route, а не пятым элементом bottom navigation.

### Tablet

Допускается master/detail для списка пространств или диалогов + активного контекста.

### Desktop

Двух- или трёхколоночный layout только когда каждая колонка несёт постоянную ценность. Пустые боковые панели ради «desktop-вида» не используются.

## UX состояния обязательны для каждого feature

Для каждой новой функции проектируем:

1. first-use;
2. normal;
3. loading;
4. empty;
5. partial data;
6. offline/reconnecting;
7. permission denied;
8. validation error;
9. destructive action;
10. mobile narrow viewport;
11. keyboard/focus flow;
12. reduced motion.

## Миграция старого UI

Порядок обновления:

1. design tokens и global primitives;
2. app shell/navigation;
3. auth + registration;
4. Persona/profile;
5. messaging + composer;
6. Space screens;
7. social intent/privacy;
8. notifications;
9. moderation/admin;
10. legacy cleanup.

Мы не делаем big-bang redesign. Каждый продуктовый этап переводит затронутые экраны на новый kit и оставляет интерфейс рабочим между этапами.

## Definition of Done для UI/UX

Feature не считается завершённой, если:

- используются новые backend-сущности, но UI всё ещё говорит legacy-терминами;
- нет mobile layout;
- отсутствуют loading/empty/error состояния;
- действие недоступно с keyboard;
- важное состояние кодируется только цветом;
- пользователь не понимает, что произойдёт после destructive action;
- screen нарушает Account != Persona или Reputation != Permission;
- engagement/support UI создаёт leaderboard/pay-to-status pressure;
- gift UI создаёт wallet/currency semantics до появления реального financial domain;
- новая функция ухудшает путь к общению.
