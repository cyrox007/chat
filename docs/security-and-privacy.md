# Безопасность и приватность PubChat

## Модель доверия

Backend является единственным источником решения о доступе. Проверки во Vue нужны для UX, но не заменяют server-side authorization.

## Сессии

- access JWT короткоживущий и хранится browser SPA только в памяти;
- refresh session использует HttpOnly cookie;
- refresh token material хранится server-side в hashed representation;
- access/refresh/CSRF secrets разные и не короче 32 символов;
- bearer/token material не должен попадать в application logs.

## WebSocket

JWT не передаётся в path/query. Authenticated HTTP выдаёт короткоживущий one-time scoped ticket, который отправляется первым WebSocket frame и consume-ится один раз.

## CSRF и CORS

Cookie-based state-changing HTTP flows используют CSRF protection. `FRONTEND_URL` задаёт разрешённые origins. Production должен использовать HTTPS.

## Account и Persona

Security/trust/lifecycle принадлежат Account. Persona — публичная projection. Публичный API не должен отдавать credential, password hash, private email/phone или внутренние moderation fields.

## Privacy

Profile discovery/direct access и appearance используют одинаковую privacy boundary. Location показывается только при consent. DM policy применяется server-side.

## Block

Block — Account-level и проверяется в обе стороны. Любая новая social surface должна отдельно проверить, не создаёт ли она обход block. Это относится к profiles, DM, discovery, Conversation Rounds и будущим recommendation/gift flows.

## Spaces

Space role scoped конкретным Space. Owner/moderator не получает platform authority. Private Space — invite-only. WebSocket ticket для Space зависит от canonical active membership/restriction.

## Moderation

Reports приватны. Значимое action имеет reason/state и, где предусмотрено, appeal. Original decision maker не должен подтверждать собственную апелляцию. Ограничение доступа не оформляется игровой/тюремной метафорой.

## Notifications

Reminder preference и notification inbox принадлежат Account. Нет cross-account list/read API. Manager Space не видит, кто включил личное напоминание. Notification context не является authorization token и не обходит membership/visibility.

## Файлы

Текущий upload layer остаётся compatibility area. Перед beta необходим отдельный security review MIME/content validation, malware/content scanning strategy, object storage и public URL policy.

## Security review для нового feature

Проверить:

1. Можно ли подставить чужой Account UID и изменить его состояние?
2. Есть ли mass assignment?
3. Не раскрывает ли `404/403` или metadata существование private ресурса?
4. Учитывается ли Account-level block?
5. Проверяется ли Space membership/role server-side?
6. Нужен ли DB constraint против race?
7. Может ли retry создать duplicate durable state?
8. Не попадает ли secret в URL/log/localStorage?
9. Не даёт ли cosmetic/payment field authority/trust?
10. Не позволяет ли новая Persona обойти Account restriction?

## До beta обязательно

- production-like session/cookie/CSRF review;
- upload/media review;
- PostgreSQL/Redis integration tests;
- privacy side-channel review;
- dependency/security scan policy;
- observability без credential leakage;
- отсутствие известных P0/P1 security blockers.

Уязвимости не следует публиковать как exploit instructions в открытом issue до определения процесса responsible disclosure; отдельная security policy будет добавлена перед публичным beta launch.
