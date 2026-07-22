"""Banka onaylı normal kullanıcı oturumunun BFF HTTP sınırı."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Sequence
from typing import NoReturn
from urllib.parse import urlsplit

from fastapi import Request, Response

from veri_kalitesi.api.errors import (
    ApiAuthenticationError,
    ApiConfigurationError,
    ApiCsrfError,
    ApiSessionUnavailableError,
)
from veri_kalitesi.identity import (
    ActorContext,
    ActorContextValidationError,
    SessionActivity,
    SessionDeniedError,
    SessionGrant,
    SessionService,
    SessionUnavailableError,
)

SESSION_COOKIE_NAME = "__Host-session"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class BffSessionBoundary:
    """Cookie, CSRF ve session servisinin güvenilir HTTP adaptörü."""

    def __init__(
        self,
        session_service: SessionService,
        *,
        allowed_origins: Sequence[str],
    ) -> None:
        self.session_service = session_service
        self.allowed_origins = frozenset(_normalize_origin(origin) for origin in allowed_origins)
        if not self.allowed_origins:
            raise ApiConfigurationError(
                "At least one explicit BFF origin is required.",
                "api-startup",
            )

    def attach_session(self, response: Response, grant: SessionGrant) -> None:
        """Güvenilir IdP callback sonucunu tarayıcı BFF taşımasına bağlar."""

        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=_encode_secret(grant.credential),
            secure=True,
            httponly=True,
            samesite="lax",
            path="/",
        )
        response.headers[CSRF_HEADER_NAME] = _encode_secret(grant.csrf_token)
        response.headers["Cache-Control"] = "no-store"

    def resolve(self, request: Request) -> ActorContext:
        credential = self._session_credential(request)
        try:
            return self.session_service.validate(
                credential,
                request.state.correlation_id,
                activity=SessionActivity.BACKGROUND,
            )
        except (ActorContextValidationError, SessionDeniedError) as exc:
            raise ApiAuthenticationError(
                "Authenticated session could not be established.",
                request.state.correlation_id,
            ) from exc
        except SessionUnavailableError as exc:
            raise ApiSessionUnavailableError(
                "Session service is unavailable.",
                request.state.correlation_id,
            ) from exc

    def protect_state_changing(self, request: Request) -> ActorContext | None:
        if request.method.upper() in SAFE_HTTP_METHODS:
            return None
        self._validate_request_origin(request)
        credential = self._session_credential(request)
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        if csrf_header is None:
            self._csrf_denied(request)
        try:
            csrf_token = _decode_secret(csrf_header)
        except ValueError as exc:
            raise ApiCsrfError(
                "State-changing request could not be verified.",
                request.state.correlation_id,
            ) from exc
        try:
            context = self.session_service.validate_csrf(
                credential,
                csrf_token,
                request.state.correlation_id,
                activity=SessionActivity.USER_INTERACTION,
            )
        except SessionDeniedError as exc:
            if exc.reason_code == "CSRF_VALIDATION_FAILED":
                raise ApiCsrfError(
                    "State-changing request could not be verified.",
                    request.state.correlation_id,
                ) from exc
            raise ApiAuthenticationError(
                "Authenticated session could not be established.",
                request.state.correlation_id,
            ) from exc
        except ActorContextValidationError as exc:
            raise ApiCsrfError(
                "State-changing request could not be verified.",
                request.state.correlation_id,
            ) from exc
        except SessionUnavailableError as exc:
            raise ApiSessionUnavailableError(
                "Session service is unavailable.",
                request.state.correlation_id,
            ) from exc
        request.state.session_credential = credential
        request.state.actor_context = context
        return context

    def logout(self, request: Request, response: Response) -> None:
        credential = getattr(request.state, "session_credential", None)
        if not isinstance(credential, bytes):
            raise ApiAuthenticationError(
                "Authenticated session could not be established.",
                request.state.correlation_id,
            )
        try:
            self.session_service.logout(credential, request.state.correlation_id)
        except (ActorContextValidationError, SessionDeniedError) as exc:
            raise ApiAuthenticationError(
                "Authenticated session could not be established.",
                request.state.correlation_id,
            ) from exc
        except SessionUnavailableError as exc:
            raise ApiSessionUnavailableError(
                "Session service is unavailable.",
                request.state.correlation_id,
            ) from exc
        response.delete_cookie(
            key=SESSION_COOKIE_NAME,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
        response.headers["Cache-Control"] = "no-store"

    def _session_credential(self, request: Request) -> bytes:
        cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
        if cookie_value is None:
            raise ApiAuthenticationError(
                "Authenticated session could not be established.",
                request.state.correlation_id,
            )
        try:
            return _decode_secret(cookie_value)
        except ValueError as exc:
            raise ApiAuthenticationError(
                "Authenticated session could not be established.",
                request.state.correlation_id,
            ) from exc

    def _validate_request_origin(self, request: Request) -> None:
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        fetch_site = request.headers.get("Sec-Fetch-Site")
        if origin is None or referer is None or fetch_site not in {"same-origin", "same-site"}:
            self._csrf_denied(request)
        try:
            normalized_origin = _normalize_origin(origin)
            normalized_referer = _origin_from_referer(referer)
        except ApiConfigurationError as exc:
            raise ApiCsrfError(
                "State-changing request could not be verified.",
                request.state.correlation_id,
            ) from exc
        if (
            normalized_origin not in self.allowed_origins
            or normalized_referer not in self.allowed_origins
            or normalized_origin != normalized_referer
        ):
            self._csrf_denied(request)

    def _csrf_denied(self, request: Request) -> NoReturn:
        raise ApiCsrfError(
            "State-changing request could not be verified.",
            request.state.correlation_id,
        )


def _encode_secret(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_secret(value: str) -> bytes:
    if not value or any(character.isspace() for character in value):
        raise ValueError("Invalid opaque value.")
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(
            value + padding,
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid opaque value.") from exc
    if not decoded or _encode_secret(decoded) != value:
        raise ValueError("Invalid opaque value.")
    return decoded


def _normalize_origin(origin: str) -> str:
    stripped = origin.strip()
    parsed = urlsplit(stripped)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ApiConfigurationError("BFF origins must be explicit origins.", "api-startup")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _origin_from_referer(referer: str) -> str:
    parsed = urlsplit(referer.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ApiConfigurationError("BFF referer is invalid.", "request")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
