# PubChat — руководство пользователя

Документ описывает пользовательские функции выпущенного checkpoint PubChat `0.5.3-alpha.1`.

## 1. Account и Persona

PubChat разделяет учётную запись и публичный образ.

- **Account** — вход, безопасность, сессии, platform permissions и ограничения.
- **Persona** — имя, handle, аватар, bio, social intent и публичное оформление.

Пользователь взаимодействует с другими людьми через Persona. Account не должен визуально подменять Persona.

### Регистрация

Откройте «Создать образ», заполните регистрационные данные и создайте Persona. После успешной регистрации SPA получает короткоживущий access token, а долговременная refresh-сессия хранится в HttpOnly cookie.

### Вход и восстановление сессии

После перезагрузки страницы SPA не хранит access JWT на диске. Клиент восстанавливает короткую access-сессию через refresh cookie. Если refresh больше недействителен, пользователь возвращается на экран входа.

## 2. Профиль и приватность

В профиле можно управлять отображаемым именем, bio, location, social intent и политикой личных сообщений.

Политики DM:

- `everyone` — новый DM может начать любой доступный пользователь;
- `shared_spaces` — требуется общее активное Space;
- `mutual` — требуется взаимная friendship;
- `nobody` — новые личные разговоры закрыты.

Account-level block всегда имеет приоритет.

## 3. Стиль Persona

Раздел «Стиль образа» позволяет выбрать allowlisted cosmetic presets: accent, фон, рамку аватара и короткую status line.

Оформление не влияет на trust, permissions, moderation power или discovery ranking. Публичный appearance показывается только если viewer имеет право видеть сам профиль.

## 4. Living Spaces

Space — основная социальная единица PubChat: сообщество с участниками, ролями, правилами, событиями, историей и оформлением.

Visibility:

- **public** — виден в discovery;
- **unlisted** — обычно доступен по прямой ссылке;
- **private** — invite-only.

Membership policy:

- **open** — можно войти сразу;
- **request** — пользователь отправляет заявку;
- **invite** — требуется приглашение.

Scoped роли: `owner`, `moderator`, `member`. Moderator одного Space не становится platform moderator.

## 5. Разговор в Space

После входа открывается realtime-разговор. SPA различает `connecting`, `authenticating`, `connected`, `reconnecting`, `offline`, `restricted` и восстанавливает соединение без полной перезагрузки страницы.

WebSocket использует одноразовый короткоживущий ticket. Bearer/JWT не передаётся в URL.

## 6. Люди и социальные связи

Раздел «Люди» использует privacy-aware discovery. Доступны follow/unfollow, friend request, accept/reject/remove friendship и block/unblock.

Block действует на Account-level в обе стороны и влияет на discovery, профиль, DM, Conversation Round responses и gifts.

## 7. Приглашения в Spaces

Manager закрытого пространства может отправить account-bound invite. Получатель видит его в «Приглашениях» и принимает либо отклоняет. При accept backend повторно проверяет актуальные capacity, restrictions, block и membership conditions.

## 8. Личные сообщения

Раздел «Сообщения» работает через отдельный realtime channel. После reconnect клиент восстанавливает активный диалог и subscriptions. Read receipt можно изменить только для сообщения, получателем которого является текущий Account.

## 9. Центр пространства

В «Центре пространства» находятся Rules, Events и append-only History. Rules/Events управляются scoped roles. История сообщества не раскрывает приватные moderation reports.

## 10. Жизнь пространства

Раздел «Жизнь пространства» объединяет Space Appearance и Activities.

### Appearance

Owner/moderator может выбрать тему, cover preset, ambient icon и welcome line. Обычный participant видит оформление, но не меняет его.

### Activities

Участник может создать социальную активность: разговор, викторину, игру, совместный просмотр, творчество или локальную встречу.

Activity содержит название, описание, тип, дату/время, recurrence `none/daily/weekly/monthly` и RSVP.

Recurring Activity хранится как один шаблон. Backend вычисляет ближайший `next_starts_at`; бесконечная серия строк в БД не создаётся.

RSVP: «Интересно», «Иду» или снять отметку.

## 11. Conversation Rounds

Conversation Round — social prompt внутри Activity.

Форматы: `icebreaker`, `choice`, `story_chain`. На Activity может быть только один открытый round. Каждый Account имеет максимум один response; повторная отправка обновляет собственный ответ.

Нет score, rank, winner, prize, stake, currency или pay-to-win механики.

## 12. Достижения

Earned achievements выдаёт только backend system hooks. Первые отметки: `first_host`, `conversation_starter`, `first_round_response`.

Публично виден shelf. Дополнительный source/context доступен только владельцу. Достижения — косметическая история участия, а не рейтинг человека.

## 13. Safety Center

В «Безопасности» пользователь может отправить report на участника конкретного Space, видеть статус своих reports, видеть применённые к нему moderation actions и подать доступную апелляцию.

Reports не публикуются всему Space.

## 14. Moderation queue

Owner/moderator имеет отдельную scoped queue. Решения: warning или restrict access с причиной и при необходимости сроком. Апелляция рассматривается отдельно; автор исходного решения не должен сам подтверждать собственную апелляцию.

В интерфейсе нет «тюрьмы», «надзирателей» и игровой метафоры наказаний.

## 15. Напоминания и notification inbox

В `0.5.2-alpha.1` Activities получили concrete bounded occurrences и opt-in in-app reminders.

### Как включить напоминание

1. Откройте Space.
2. Перейдите в «Жизнь».
3. Найдите нужную Activity.
4. Выберите срок: за 15 минут, за час или за день.
5. Нажмите «Напомнить».

Настройку можно изменить или отключить в той же карточке.

### Где смотреть уведомления

В верхней панели есть bell indicator. Раздел «Напоминания» показывает личный inbox. Карточку можно открыть, после чего PubChat ведёт в обычный Space Life route и повторно применяет все membership/visibility правила.

Можно отметить одно уведомление или все как прочитанные.

### Правила reminders

- reminders включаются только пользователем;
- они принадлежат Account и не видны manager Space;
- максимум одно notification на concrete occurrence;
- максимум 200 активных Activity reminders на Account;
- recurring occurrences materialize только в bounded horizon;
- приложение периодически выполняет idempotent in-app sync;
- browser/native push пока не используется.

### Время и DST

Activity сейчас хранит canonical UTC instant. Для recurring schedule пока не сохраняется IANA timezone name, поэтому при переходе летнего/зимнего времени локальное wall-clock время weekly/monthly серии может сдвинуться на час. Reminder следует фактическому UTC schedule. Это известное alpha-ограничение и будет исправлено до beta на backend, а не client-side костылём.

## 16. Поддержка Persona и Spaces

В `0.5.3-alpha.1` появились бесплатные внутренние gifts как спокойный способ сказать «спасибо». Это не магазин и не платёжная система.

### Persona support

В «Стиле образа» владелец может отдельно включить получение gifts и добавить короткую подпись. По умолчанию support выключен.

В обычном Persona profile отображается агрегированный shelf: вид gift и количество. Другой пользователь может открыть picker и отправить один из allowlisted gestures, если support включён и privacy/block policy разрешает взаимодействие.

Владелец видит свою private received history с sender label и optional message. Эта история не показывается другим пользователям.

### Space support

У Space есть отдельный раздел «Поддержка» `/spaces/:uid/support`.

- shelf показывает агрегированные gifts;
- отправлять gift может только active member при включённом support;
- owner/moderator управляет opt-in settings;
- owner/moderator видит private received history;
- owner не может отправлять gift собственному Space.

### Правила support

- gift бесплатный и не имеет цены/валюты;
- support не меняет trust, permissions, moderation power или discovery ranking;
- sender не получает score/rank/streak;
- Persona нельзя подарить gift самому себе;
- Account-level block применяется и к support;
- максимум 20 внутренних gifts с Account за rolling 24 часа;
- параллельные sends одного Account сериализуются server-side для соблюдения лимита;
- публичный shelf не показывает sender/message;
- append-only ledger сохраняет historical snapshot даже после удаления исходной Persona/Space;
- реальных checkout/payment/wallet/balance/refund/payout функций в `0.5.3` нет.

## 17. Что PubChat сознательно не делает

- не продаёт moderation roles;
- не продаёт trust;
- не использует платный рейтинг человека;
- не делает dating swipe основным сценарием;
- не превращает achievements или gifts в leaderboard;
- не использует casino/loot-box/stake механику;
- не включает reminders или support без согласия пользователя;
- не использует gift count как discovery/trust signal;
- не скрывает причины moderation decisions за игровой терминологией.
