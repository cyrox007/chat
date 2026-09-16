from __future__ import annotations

import asyncio
import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from uuid import UUID

from settings import config


@dataclass(frozen=True)
class EmailDeliveryRequest:
    delivery_uid: UUID
    recipient: str
    unread_count: int
    dialog_count: int


@dataclass(frozen=True)
class EmailProviderResult:
    provider_message_id: str


class EmailProviderError(RuntimeError):
    def __init__(self, failure_class: str, *, retryable: bool) -> None:
        super().__init__(failure_class)
        self.failure_class = failure_class
        self.retryable = retryable


def deterministic_message_id(delivery_uid: UUID, from_email: str) -> str:
    domain = from_email.rsplit("@", 1)[-1].strip().lower() if "@" in from_email else "pubchat.local"
    return f"<pubchat-{delivery_uid}@{domain}>"


def messenger_url() -> str:
    frontend = next((item.strip().rstrip("/") for item in config.FRONTEND_URL if item.strip()), "")
    return f"{frontend}/messenger" if frontend else "/messenger"


def build_unread_dm_email(request: EmailDeliveryRequest) -> EmailMessage:
    message_id = deterministic_message_id(request.delivery_uid, config.MESSAGE_EMAIL_FROM_EMAIL)
    message = EmailMessage()
    message["Subject"] = "У вас есть непрочитанные сообщения в PubChat"
    message["From"] = formataddr((config.MESSAGE_EMAIL_FROM_NAME, config.MESSAGE_EMAIL_FROM_EMAIL))
    message["To"] = request.recipient
    message["Message-ID"] = message_id
    message["Auto-Submitted"] = "auto-generated"
    message["X-Auto-Response-Suppress"] = "All"

    count = max(1, int(request.unread_count))
    dialogs = max(1, int(request.dialog_count))
    url = messenger_url()
    message.set_content(
        "PubChat напоминает о непрочитанных личных сообщениях.\n\n"
        f"Непрочитанных сообщений: {count}. Диалогов: {dialogs}.\n"
        f"Открыть Messenger: {url}\n\n"
        "Текст личных сообщений намеренно не включён в это письмо. "
        "Уведомления можно отключить в настройках PubChat."
    )
    message.add_alternative(
        "<html><body>"
        "<p>PubChat напоминает о непрочитанных личных сообщениях.</p>"
        f"<p><strong>Непрочитанных сообщений:</strong> {count}<br>"
        f"<strong>Диалогов:</strong> {dialogs}</p>"
        f'<p><a href="{url}">Открыть Messenger</a></p>'
        "<p>Текст личных сообщений намеренно не включён в это письмо. "
        "Уведомления можно отключить в настройках PubChat.</p>"
        "</body></html>",
        subtype="html",
    )
    return message


def _classify_smtp_exception(exc: BaseException) -> EmailProviderError:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return EmailProviderError("smtp_authentication", retryable=False)
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return EmailProviderError("recipient_rejected", retryable=False)
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return EmailProviderError("sender_rejected", retryable=False)
    if isinstance(exc, smtplib.SMTPResponseException):
        code = int(getattr(exc, "smtp_code", 0) or 0)
        return EmailProviderError(f"smtp_{code or 'response'}", retryable=400 <= code < 500)
    if isinstance(exc, (TimeoutError, socket.timeout, ConnectionError, OSError, smtplib.SMTPServerDisconnected)):
        return EmailProviderError("smtp_unavailable", retryable=True)
    return EmailProviderError("smtp_error", retryable=True)


class SmtpEmailProvider:
    @property
    def configured(self) -> bool:
        return config.message_email_delivery_configured()

    async def send(self, request: EmailDeliveryRequest) -> EmailProviderResult:
        if not self.configured:
            raise EmailProviderError("smtp_not_configured", retryable=False)
        message = build_unread_dm_email(request)
        try:
            await asyncio.to_thread(self._send_sync, message)
        except EmailProviderError:
            raise
        except Exception as exc:
            raise _classify_smtp_exception(exc) from exc
        return EmailProviderResult(provider_message_id=str(message["Message-ID"]))

    def _send_sync(self, message: EmailMessage) -> None:
        smtp_class = smtplib.SMTP_SSL if config.MESSAGE_EMAIL_SMTP_USE_SSL else smtplib.SMTP
        kwargs = {
            "host": config.MESSAGE_EMAIL_SMTP_HOST,
            "port": config.MESSAGE_EMAIL_SMTP_PORT,
            "timeout": config.MESSAGE_EMAIL_SMTP_TIMEOUT_SECONDS,
        }
        if config.MESSAGE_EMAIL_SMTP_USE_SSL:
            kwargs["context"] = ssl.create_default_context()

        with smtp_class(**kwargs) as client:
            client.ehlo()
            if config.MESSAGE_EMAIL_SMTP_STARTTLS and not config.MESSAGE_EMAIL_SMTP_USE_SSL:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if config.MESSAGE_EMAIL_SMTP_USERNAME:
                client.login(config.MESSAGE_EMAIL_SMTP_USERNAME, config.MESSAGE_EMAIL_SMTP_PASSWORD)
            refused = client.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
