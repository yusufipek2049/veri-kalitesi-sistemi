"""SMTP ve webhook bildirim taşıyıcıları.

Taşıyıcılar veri-minimum içerik üretir, sırları yalnız çalışma anında çözer ve
altyapı ayrıntılarını teslimat hata sınıflarına dönüştürür.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from email.message import EmailMessage
from email.utils import parseaddr
import http.client
import ipaddress
import json
from pathlib import Path
import re
import smtplib
import socket
import ssl
from typing import Any, Callable, Protocol
from urllib.parse import urlsplit

from veri_kalitesi.notifications.errors import (
    PermanentNotificationTransportError,
    TemporaryNotificationTransportError,
)
from veri_kalitesi.notifications.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationEvent,
)

_FORBIDDEN_CONFIG_KEYS = frozenset(
    {"password", "passwd", "secret", "token", "credential", "authorization"}
)


class NotificationChannelAdapter(Protocol):
    """Kanal-bağımsız teslimat adaptörü sözleşmesi."""

    def deliver(
        self,
        event: NotificationEvent,
        delivery: NotificationDelivery,
        channel: NotificationChannel,
    ) -> bool: ...


class NotificationSecretResolver(Protocol):
    """Salt-okunur sağlayıcıdan sır alan sınır sözleşmesi."""

    def resolve(self, secret_reference: str) -> Mapping[str, Any]: ...


class MountedNotificationSecretResolver:
    """Yerel salt-okunur mount'tan yalnız izinli bildirim sır alanlarını çözer."""

    _REFERENCE = re.compile(r"secret://local/([a-zA-Z0-9][a-zA-Z0-9_-]{0,79})")
    _FIELDS = ("username", "password", "authorization")

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("Mounted notification secret root is unavailable.")

    def resolve(self, secret_reference: str) -> Mapping[str, Any]:
        match = self._REFERENCE.fullmatch(secret_reference)
        if match is None:
            raise ValueError("Notification secret reference is not allowed.")
        directory = (self._root / match.group(1)).resolve(strict=True)
        if directory.parent != self._root or not directory.is_dir():
            raise ValueError("Notification secret reference is outside the mount.")
        values: dict[str, str] = {}
        for field in self._FIELDS:
            path = directory / field
            if not path.exists():
                continue
            if path.is_symlink():
                raise ValueError("Notification secret symlinks are not allowed.")
            resolved = path.resolve(strict=True)
            if resolved.parent != directory or not resolved.is_file():
                raise ValueError("Notification secret file is unavailable.")
            value = resolved.read_text(encoding="utf-8").strip()
            if not value:
                raise ValueError("Notification secret value is empty.")
            values[field] = value
        if not values:
            raise ValueError("Notification secret reference could not be resolved.")
        return values


class SMTPClient(Protocol):
    def starttls(self, *, context: ssl.SSLContext) -> Any: ...

    def login(self, user: str, password: str) -> Any: ...

    def send_message(self, message: EmailMessage) -> Mapping[str, Any]: ...

    def quit(self) -> Any: ...

    def close(self) -> Any: ...


class SMTPClientFactory(Protocol):
    def __call__(
        self, host: str, port: int, *, timeout: float, use_ssl: bool
    ) -> SMTPClient: ...


def _default_smtp_factory(
    host: str, port: int, *, timeout: float, use_ssl: bool
) -> SMTPClient:
    client_type = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    return client_type(host=host, port=port, timeout=timeout)


class SMTPNotificationAdapter:
    """Standart kütüphane ile zaman aşımlı SMTP teslimatı."""

    def __init__(
        self,
        secret_resolver: NotificationSecretResolver,
        *,
        client_factory: SMTPClientFactory = _default_smtp_factory,
        timeout_seconds: float = 10.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("SMTP timeout must be positive.")
        self._secret_resolver = secret_resolver
        self._client_factory = client_factory
        self._timeout_seconds = timeout_seconds

    def deliver(
        self,
        event: NotificationEvent,
        delivery: NotificationDelivery,
        channel: NotificationChannel,
    ) -> bool:
        config = _safe_config(channel.target_config)
        host = _required_text(config, "host")
        sender = _email_address(config, "from_address")
        recipient = _email_address(config, "to_address")
        port = _port(config.get("port", 465 if config.get("use_ssl", True) else 587))
        use_ssl = _boolean(config.get("use_ssl", True), "use_ssl")
        starttls = _boolean(config.get("starttls", not use_ssl), "starttls")
        if use_ssl and starttls:
            raise PermanentNotificationTransportError("INVALID_SMTP_CONFIGURATION")

        username: str | None = None
        password: str | None = None
        if channel.secret_ref is not None:
            try:
                secret = self._secret_resolver.resolve(channel.secret_ref)
                username = _secret_text(secret, "username")
                password = _secret_text(secret, "password")
            except PermanentNotificationTransportError:
                raise
            except Exception as exc:
                raise TemporaryNotificationTransportError("SECRET_RESOLUTION_FAILED") from exc

        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = f"Data quality notification: {event.event_type.value}"
        message.set_content(
            "A data quality event requires attention. "
            f"Type: {event.event_type.value}. Delivery reference: {delivery.delivery_id}."
        )

        client: SMTPClient | None = None
        try:
            client = self._client_factory(
                host, port, timeout=self._timeout_seconds, use_ssl=use_ssl
            )
            if starttls:
                client.starttls(context=ssl.create_default_context())
            if username is not None and password is not None:
                client.login(username, password)
            refused = client.send_message(message)
            if refused:
                raise PermanentNotificationTransportError("SMTP_RECIPIENT_REJECTED")
            try:
                client.quit()
            except Exception:
                # Sunucu mesajı kabul ettikten sonraki bağlantı kapatma hatası,
                # aynı iletiyi yeniden göndermeye neden olmamalıdır.
                client.close()
            client = None
            return True
        except PermanentNotificationTransportError:
            raise
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused) as exc:
            raise PermanentNotificationTransportError("SMTP_PERMANENT_ERROR") from exc
        except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as exc:
            code = int(getattr(exc, "smtp_code", 500))
            error_type = (
                TemporaryNotificationTransportError
                if 400 <= code < 500
                else PermanentNotificationTransportError
            )
            error_class = "SMTP_TEMPORARY_ERROR" if code < 500 else "SMTP_PERMANENT_ERROR"
            raise error_type(error_class) from exc
        except (smtplib.SMTPException, OSError, TimeoutError) as exc:
            raise TemporaryNotificationTransportError("SMTP_TEMPORARY_ERROR") from exc
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass


class WebhookHttpClient(Protocol):
    """Testlerde ağsız değiştirilebilen minimal HTTP istemcisi."""

    def post(
        self,
        url: str,
        *,
        resolved_address: str,
        body: bytes,
        headers: Mapping[str, str],
        timeout: float,
    ) -> int: ...


class StandardLibraryWebhookHttpClient:
    """Doğrulanmış IP'ye sabitlenen, redirect izlemeyen HTTPS istemcisi."""

    def post(
        self,
        url: str,
        *,
        resolved_address: str,
        body: bytes,
        headers: Mapping[str, str],
        timeout: float,
    ) -> int:
        parsed = urlsplit(url)
        host = parsed.hostname
        if host is None:
            raise ValueError("Webhook host is required.")
        port = parsed.port or 443
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        raw_socket: socket.socket | None = None
        connection: http.client.HTTPSConnection | None = None
        try:
            raw_socket = socket.create_connection((resolved_address, port), timeout=timeout)
            tls_socket = ssl.create_default_context().wrap_socket(
                raw_socket,
                server_hostname=host,
            )
            raw_socket = None
            connection = http.client.HTTPSConnection(host, port=port, timeout=timeout)
            connection.sock = tls_socket
            connection.request("POST", path, body=body, headers=dict(headers))
            response = connection.getresponse()
            return int(response.status)
        finally:
            if connection is not None:
                connection.close()
            if raw_socket is not None:
                raw_socket.close()


AddressResolver = Callable[[str, int], Sequence[str]]


def _resolve_addresses(host: str, port: int) -> tuple[str, ...]:
    return tuple(
        str(item[4][0])
        for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    )


class WebhookNotificationAdapter:
    """HTTPS POST taşıyıcısı; özel/yerel hedefleri ve redirect'leri reddeder."""

    def __init__(
        self,
        secret_resolver: NotificationSecretResolver,
        *,
        http_client: WebhookHttpClient | None = None,
        address_resolver: AddressResolver = _resolve_addresses,
        timeout_seconds: float = 5.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Webhook timeout must be positive.")
        self._secret_resolver = secret_resolver
        self._http_client = http_client or StandardLibraryWebhookHttpClient()
        self._address_resolver = address_resolver
        self._timeout_seconds = timeout_seconds

    def deliver(
        self,
        event: NotificationEvent,
        delivery: NotificationDelivery,
        channel: NotificationChannel,
    ) -> bool:
        config = _safe_config(channel.target_config)
        url = _required_text(config, "url")
        addresses = self._validate_public_https_target(url)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Idempotency-Key": delivery.delivery_id,
        }
        if channel.secret_ref is not None:
            try:
                secret = self._secret_resolver.resolve(channel.secret_ref)
                headers["Authorization"] = _secret_text(secret, "authorization")
            except PermanentNotificationTransportError:
                raise
            except Exception as exc:
                raise TemporaryNotificationTransportError("SECRET_RESOLUTION_FAILED") from exc
        body = json.dumps(
            {
                "delivery_id": delivery.delivery_id,
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "scope_type": event.scope_type.value,
                "occurred_at": event.occurred_at.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            status = self._http_client.post(
                url,
                resolved_address=addresses[0],
                body=body,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except (http.client.HTTPException, OSError, TimeoutError) as exc:
            raise TemporaryNotificationTransportError("WEBHOOK_TEMPORARY_ERROR") from exc
        if 200 <= status < 300:
            return True
        if 500 <= status < 600:
            raise TemporaryNotificationTransportError("WEBHOOK_SERVER_ERROR")
        raise PermanentNotificationTransportError("WEBHOOK_CLIENT_ERROR")

    def _validate_public_https_target(self, url: str) -> tuple[str, ...]:
        try:
            parsed = urlsplit(url)
            port = parsed.port or 443
        except ValueError as exc:
            raise PermanentNotificationTransportError("WEBHOOK_TARGET_INVALID") from exc
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise PermanentNotificationTransportError("WEBHOOK_TARGET_INVALID")
        try:
            addresses = self._address_resolver(parsed.hostname, port)
        except OSError as exc:
            raise TemporaryNotificationTransportError("WEBHOOK_DNS_ERROR") from exc
        if not addresses:
            raise TemporaryNotificationTransportError("WEBHOOK_DNS_ERROR")
        try:
            if any(not ipaddress.ip_address(address).is_global for address in addresses):
                raise PermanentNotificationTransportError("WEBHOOK_TARGET_FORBIDDEN")
        except ValueError as exc:
            raise PermanentNotificationTransportError("WEBHOOK_TARGET_INVALID") from exc
        return tuple(addresses)


def _safe_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(config, Mapping):
        raise PermanentNotificationTransportError("INVALID_CHANNEL_CONFIGURATION")
    if any(str(key).lower() in _FORBIDDEN_CONFIG_KEYS for key in config):
        raise PermanentNotificationTransportError("PLAINTEXT_SECRET_FORBIDDEN")
    return config


def _required_text(values: Mapping[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PermanentNotificationTransportError("INVALID_CHANNEL_CONFIGURATION")
    return value.strip()


def _secret_text(values: Mapping[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise PermanentNotificationTransportError("SECRET_VALUE_INVALID")
    return value


def _email_address(values: Mapping[str, Any], key: str) -> str:
    value = _required_text(values, key)
    _, parsed = parseaddr(value)
    if parsed != value or "@" not in parsed or any(char.isspace() for char in parsed):
        raise PermanentNotificationTransportError("INVALID_EMAIL_ADDRESS")
    return parsed


def _port(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
        raise PermanentNotificationTransportError("INVALID_SMTP_CONFIGURATION")
    return value


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise PermanentNotificationTransportError(f"INVALID_{field.upper()}")
    return value
