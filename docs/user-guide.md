# PubChat — руководство пользователя

Документ описывает пользовательские функции PubChat. Если функция помечена **In development**, она существует только в активной ветке и ещё не считается частью выпущенного `main`.

Текущий release: `0.5.1-alpha.1`.

## 1. Account и Persona

PubChat разделяет учётную запись и публичный образ.

- **Account** — вход, безопасность, сессии, platform permissions и ограничения.
- **Persona** — имя, handle, аватар, bio, social intent и публичное оформление.

Пользователь взаимодействует с другими людьми через Persona. Account не должен визуально подменять Persona.

### Регистрация

Откройте «Создать образ», заполните регистрационные данные и создайте Persona. После успешной регистрации SPA получает короткоживущий access token, а долговременная refresh-сессия хранится в HttpOnly cookie.

### Вход и восстановление сессии

После перезагрузки страницы SPA не хранит access JWT на диске. Клиент пытается восстановить новую короткую access-сессию через refresh cookie. Если refresh больше недействителен, пользователь возвращается на экран входа.

## 2. Профиль и приватность

В профиле можно изменить:

- отображаемое имя;
- bio;
- город и страну;
- social intent;
- правила личных сообщений;
- разрешение на отображение location.

Social intent сейчас используется как социальный контекст: «хочу пообщаться», «открыт знакомствам», «ищу компанию для игры», «только знакомые», «спокойный режим».

### Кто может писать лично

Доступны политики:

- `everyone` — новый DM может начать любой доступный пользователь;
- `shared_spaces` — требуется общее активное Space;
- `mutual` — требуется взаимная friendship;
- `nobody` — новые личные разговоры закрыты.

Account-level block всегда имеет приоритет над DM policy.

## 3. Стиль Persona

Раздел «Стиль образа» позволяет выбирать allowlisted cosmetic presets:

- accent;
- фон;
- рамку аватара;
- короткую status line.

Оформление не влияет на trust, permissions, moderation power, discovery ranking или возможность писать другим людям.

Публичный appearance показывается только если viewer имеет право видеть сам профиль.

## 4. Living Spaces

Space — основная социальная единица PubChat. Это не просто чат, а живое сообщество с участниками, ролями, правилами, событиями, историей и собственным оформлением.

### Discovery

Главный экран показывает доступные пространства. Карточка помогает понять:

- что это за Space;
- его цель/описание;
- кто и насколько активно там присутствует;
- что происходит;
- оформление/атмосферу.

Cosmetics не используются как платный ranking signal.

### Visibility

- **public** — виден в discovery;
- **unlisted** — обычно доступен по прямой ссылке;
- **private** — invite-only.

### Membership policy

- **open** — можно войти сразу;
- **request** — пользователь отправляет заявку;
- **invite** — требуется приглашение.

Private Space работает как invite-only и не должен превращаться в скрытый способ обхода membership policy.

### Роли внутри Space

- owner;
- moderator;
- member.

Эти роли scoped: moderator конкретного Space не становится platform moderator.

## 5. Разговор в Space

После входа в Space открывается realtime-разговор. Интерфейс различает состояния:

- connecting;
- authenticating;
- connected;
- reconnecting;
- offline;
- restricted.

При временном обрыве сети SPA пытается восстановить соединение без перезагрузки страницы. Composer блокируется, когда транспорт действительно недоступен.

WebSocket использует одноразовый короткоживущий ticket. Bearer/JWT не передаётся в URL.

## 6. Люди и социальные связи

Раздел «Люди» использует privacy-aware discovery.

Доступны:

- follow/unfollow;
- friend request;
- accept/reject friendship;
- remove friendship;
- block/unblock.

### Block

Block действует на Account-level и проверяется в обе стороны. Он влияет на discovery, прямой профиль, DM и Conversation Round responses. Новая Persona не должна обходить существующую блокировку Account.

## 7. Приглашения в Spaces

Manager закрытого пространства может найти Persona и отправить account-bound invite. Получатель видит приглашение в разделе «Приглашения» и может:

- принять;
- отклонить.

При принятии backend повторно проверяет актуальные capacity, ban/restriction, block и membership conditions. Старое приглашение не является вечным пропуском.

## 8. Личные сообщения

Раздел «Сообщения» работает через отдельный realtime channel. После reconnect клиент восстанавливает активный dialog/status subscriptions и дедуплицирует повторно доставленные сообщения.

Read receipt можно изменить только для сообщения, получателем которого является текущий Account.

## 9. Центр пространства

В «Центре пространства» доступны community-функции.

### Rules

Правила читают участники, изменяют owner/moderator. Правила принадлежат Space и не исчезают при удалении аккаунта автора.

### Events

События имеют время, статус и scoped управление. Время нормализуется backend в UTC.

### History

История — append-only журнал значимых community changes. Она не является публичным журналом конфликтов и не раскрывает приватные moderation reports.

## 10. Жизнь пространства

Раздел «Жизнь пространства» объединяет оформление и Activities.

### Space Appearance

Owner/moderator может выбрать тему, cover preset, ambient icon и welcome line. Обычный participant видит оформление, но не меняет его.

### Activities

Участник может создать социальную активность: разговор, викторину, игру, совместный просмотр, творчество или локальную встречу.

Activity содержит:

- название и описание;
- тип;
- дату/время;
- recurrence `none/daily/weekly/monthly`;
- RSVP.

Recurring Activity хранится как один шаблон. Backend вычисляет ближайший `next_starts_at`; бесконечные строки событий не создаются.

### RSVP

Можно отметить:

- «Интересно»;
- «Иду»;
- снять отметку.

RSVP доступен только активному участнику Space.

## 11. Conversation Rounds

Conversation Round — социальный prompt внутри конкретной Activity.

Форматы:

- `icebreaker` — вопрос для начала разговора;
- `choice` — выбор между двумя вариантами;
- `story_chain` — текстовая цепочка/тема.

Activity creator или scoped manager открывает и закрывает round. На Activity может быть только один открытый round.

Каждый Account имеет максимум один response на round; повторная отправка обновляет свой ответ. Для choice показывается распределение, но нет победителя.

Conversation Rounds не имеют score, rank, prize, stake, currency или pay-to-win механики.

## 12. Достижения

Earned achievements выдаёт только backend system hooks. Пользователь не может вызвать grant endpoint.

Первые достижения:

- `first_host` — создана первая Activity;
- `conversation_starter` — открыт первый Conversation Round;
- `first_round_response` — дан первый ответ в round.

В профиле виден публичный shelf. В собственной истории можно видеть дополнительный source/context. Чужим пользователям этот контекст не раскрывается.

Достижения — косметическая история участия, а не рейтинг человека.

## 13. Safety Center

В разделе «Безопасность» пользователь может:

- выбрать Space и участника;
- отправить report;
- видеть статус своих reports;
- видеть применённые к нему moderation actions;
- подать апелляцию, если она доступна.

Reports не публикуются всему Space.

## 14. Moderation queue

Owner/moderator Space получает отдельную очередь для scoped moderation.

Поддерживаются решения типа:

- warning;
- restrict access.

Решение содержит причину и при необходимости срок. Restrict синхронизируется с compatibility `RoomBan` и realtime disconnect.

Апелляция рассматривается отдельно. Автор исходного решения не должен подтверждать собственную апелляцию; overturn снимает именно связанное ограничение.

В UI сознательно нет «тюрьмы», «надзирателей» и игровой метафоры наказаний.

## 15. Напоминания и уведомления — In development (`0.5.2-alpha.x`)

В активной ветке разрабатываются concrete Activity Occurrences и приватный notification inbox.

План/текущая реализация:

- recurrence materializes только в bounded horizon;
- пользователь сам включает reminder;
- доступные lead times: 15 минут, 1 час, 1 день;
- reminders принадлежат Account и не видны manager Space;
- максимум одно reminder notification на occurrence;
- личный inbox с unread/read/read-all;
- переход из notification ведёт через обычный Space route и не обходит membership/visibility checks;
- на этом этапе нет browser/native push — только честный in-app sync.

До merge PR эта функция не считается выпущенной.

## 16. Что PubChat сознательно не делает

- не продаёт moderation roles;
- не продаёт trust;
- не использует платный рейтинг человека;
- не делает dating swipe основным сценарием;
- не превращает achievements в leaderboard;
- не использует casino/loot-box/stake механику;
- не скрывает причины moderation decisions за игровой терминологией.
