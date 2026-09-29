# Upload / media security v1

Checkpoint: `0.6.28-alpha.1`.

Этот документ фиксирует server-side security boundary для текущего upload/media pipeline PubChat. Он описывает только поддерживаемые типы и не обещает безопасный приём произвольного бинарного контента.

## Основной принцип

Файл принимается только если одновременно выполняются все условия:

1. MIME type входит в server allowlist;
2. фактический decoded/streamed размер укладывается в лимит;
3. содержимое соответствует ожидаемой сигнатуре/контейнеру;
4. storage path формируется сервером и остаётся внутри выделенного upload root;
5. Account и message-level rate/size policy разрешают операцию.

Клиентские filename, MIME и size считаются недоверенными hints.

## Поддерживаемый baseline

Текущий pipeline допускает только явно поддерживаемые raster images, audio/video, PDF и OOXML DOCX/XLSX типы, для которых реализована server-side validation.

Отдельные ограничения:

- SVG и HTML не принимаются как пользовательские uploads;
- legacy DOC/XLS не принимаются;
- произвольные ZIP/archive payloads не принимаются;
- unknown binary не получает fallback `.bin`;
- avatar path принимает только raster image types.

Расширение allowlist требует отдельного security review и tests.

## Validation

### Base64 / data URL

Parser обязан:

- принимать только ожидаемый data-URL/base64 shape;
- отклонять malformed base64;
- вычислять лимит по реально decoded bytes;
- не сохранять raw `data:` URI в durable Messenger metadata.

### Multipart

Streaming upload считает реальные bytes по мере чтения и не доверяет `UploadFile.size` или аналогичному client metadata.

Если фактический размер превышает лимит, partial output удаляется.

### Content signature

Для поддерживаемых типов проверяется минимальная magic/signature boundary.

OOXML DOCX/XLSX дополнительно должны иметь ожидаемую ZIP/Office container shape; произвольный ZIP с подходящим MIME не считается Office document.

Это не malware scanner и не Content Disarm & Reconstruction.

## Storage

Public upload:

- получает UUID-generated filename;
- не использует клиентский filename как storage path;
- пишется атомарно;
- проверяется path confinement относительно configured upload root;
- partial temporary file удаляется при validation/write failure.

Messenger и Space attachments используют один validated storage pipeline.

## Message-level limits

Media message должен соблюдать одновременно:

- максимальное число файлов;
- максимальный размер каждого файла;
- максимальный aggregate actual-byte size сообщения.

Если одна часть batch не проходит validation/limit, уже сохранённые файлы этого batch очищаются — сообщение не остаётся частично сохранённым.

## Account-level volume guard

Upload byte pressure дополнительно ограничивается distributed Redis weighted limiter.

Вес операции соответствует media byte cost, а не только количеству HTTP/WebSocket событий. Это позволяет отличать много маленьких запросов от нескольких тяжёлых uploads.

Limiter является abuse/capacity guard и не заменяет durable quota/billing model.

## Public response policy

`/uploads` responses должны включать browser hardening:

- `X-Content-Type-Options: nosniff`;
- sandboxed `Content-Security-Policy`;
- same-origin resource policy;
- document-like content отдаётся через attachment disposition, а не как inline active content.

Эти headers дополняют, но не заменяют upload validation.

## Logging / metadata

Нельзя писать в application logs:

- raw base64/data URL;
- полный private message payload;
- auth credentials/tokens;
- содержимое документа.

Durable Messenger media metadata хранит нормализованную server URL/type/size information, а не исходный raw payload.

## CI contract

Contract tests обязаны покрывать минимум:

- spoofed MIME/signature;
- unknown/SVG rejection;
- malformed base64;
- declared-size mismatch;
- multipart actual-byte overflow;
- aggregate per-message byte/file limits;
- all-or-nothing cleanup;
- DOCX/XLSX Office ZIP shape;
- public upload response headers;
- Messenger metadata normalization;
- distributed weighted media limiter.

Functional exact-head CI #758 прошёл этот baseline вместе с frontend, dependency-security и browser-smoke.

## Что остаётся до более широкого file support

До разрешения произвольных documents/archives необходим отдельный design:

- malware scanning provider/engine;
- quarantine before publication;
- Content Disarm & Reconstruction там, где применимо;
- archive recursion/bomb limits;
- password-protected/encrypted document policy;
- object/shared storage isolation;
- CDN/public URL/cache policy;
- retention/deletion semantics;
- provider outage/fail-closed behavior;
- privacy/logging/incident response.

До появления такого pipeline неподдерживаемые risky formats должны оставаться запрещёнными.
