"""Stdout JSON logging with request correlation and secret redaction."""

from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import datetime, timezone
import json
import logging
import os
import re
import sys
from collections.abc import Mapping
from typing import Any


_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_STANDARD_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__)
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "credential",
    "password",
    "passwd",
    "private_key",
    "secret",
    "token",
    "api_key",
    "connection_string",
    "database_url",
    "customer_data",
    "email",
    "personal_data",
    "phone",
    "sample",
    "ssn",
)
_URI_CREDENTIAL = re.compile(r"(?P<prefix>\b[a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@]+@", re.I)
_NAMED_SECRET = re.compile(
    r"(?i)(?P<key>password|passwd|secret|token|api[_-]?key|authorization|credential)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<value>[^\s,;}]+)",
)


def bind_correlation_id(correlation_id: str) -> Token[str | None]:
    """Bind the existing request correlation id to the current async context."""

    return _CORRELATION_ID.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    _CORRELATION_ID.reset(token)


def current_correlation_id() -> str | None:
    return _CORRELATION_ID.get()


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_text(value: str) -> str:
    value = _URI_CREDENTIAL.sub(r"\g<prefix>[REDACTED]@", value)
    return _NAMED_SECRET.sub(r"\g<key>\g<separator>[REDACTED]", value)


def redact(value: Any, *, key: object | None = None) -> Any:
    """Return a JSON-safe value with credentials and customer samples removed."""

    if key is not None and _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): redact(item, key=item_key) for item_key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return _redact_text(str(value))


class JsonFormatter(logging.Formatter):
    """Render one compact JSON object per operational log record."""

    def format(self, record: logging.LogRecord) -> str:
        correlation_id = getattr(record, "correlation_id", None) or current_correlation_id()
        document: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "correlation_id": correlation_id,
        }
        event = getattr(record, "event", None)
        if event is not None:
            document["event"] = redact(event)
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key in {
                "message",
                "asctime",
                "correlation_id",
                "event",
            }:
                continue
            document[key] = redact(value, key=key)
        if record.exc_info and record.exc_info[0] is not None:
            document["exception_class"] = record.exc_info[0].__name__
        return json.dumps(document, ensure_ascii=False, separators=(",", ":"))


def configure_logging(*, level: str | None = None) -> None:
    """Configure process loggers for JSON-only stdout emission."""

    configured_level = (level or os.environ.get("DATA_QUALITY_LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, configured_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError("DATA_QUALITY_LOG_LEVEL is invalid.")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(numeric_level)
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        framework_logger = logging.getLogger(logger_name)
        framework_logger.handlers.clear()
        framework_logger.setLevel(logging.NOTSET)
        framework_logger.propagate = True
    # The middleware emits a correlated request completion event. Uvicorn's
    # later access event runs after that context is released and would be an
    # uncorrelated duplicate.
    logging.getLogger("uvicorn.access").disabled = True
