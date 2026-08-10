"""HTTP'den veri kaynağı domain servisine ince komut adaptörü."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, NoReturn

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditResult,
)
from veri_kalitesi.audit.service import AuditSink
from veri_kalitesi.audit.errors import AuditWriteError
from veri_kalitesi.data_sources.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    SecretResolutionError,
    TechnicalError,
    ValidationError,
)
from veri_kalitesi.data_sources.models import (
    DataSourceActivationRequest,
    DataSourceActivationStatus,
)
from veri_kalitesi.data_sources.query import (
    DataSourceNotFoundError,
    DataSourceQueryAuthorizationError,
    DataSourceQueryService,
    DataSourceQueryTechnicalError,
    DataSourceView,
)
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.identity import ActorContext


@dataclass(frozen=True)
class DataSourceCommandResult:
    view: DataSourceView
    activation_request: DataSourceActivationRequest | None = None
    replayed: bool = False


class DataSourceCommandError(Exception):
    def __init__(self, code: str, correlation_id: str, *, category: str) -> None:
        super().__init__(code)
        self.code = code
        self.correlation_id = correlation_id
        self.category = category


class DataSourceCommandAdapter:
    def __init__(
        self,
        service: DataSourceService,
        query_service: DataSourceQueryService,
        security_audit: AuditSink,
    ) -> None:
        self.service = service
        self.query_service = query_service
        self.security_audit = security_audit

    def create(
        self,
        *,
        payload: Any,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult:
        context = self._require_context(actor_context)
        connection_config = {
            **dict(payload.connection_parameters),
            "host": payload.host,
            "port": payload.port,
            "database": payload.database,
            "schema": payload.schema_name,
            "ssl_mode": payload.ssl_mode,
            "connect_timeout_seconds": payload.connect_timeout_seconds,
            "statement_timeout_ms": payload.statement_timeout_ms,
        }
        try:
            source = self.service.create_data_source(
                actor_context=context,
                name=payload.name,
                source_type=payload.source_type,
                connection_config=connection_config,
                secret_reference=payload.secret_reference,
            )
            return DataSourceCommandResult(
                self.query_service.get_view_for_actor(source.data_source_id, context)
            )
        except Exception as exc:
            self._raise_command_error(exc, context)

    def test_connection(
        self, *, data_source_id: str, actor_context: ActorContext | None
    ) -> DataSourceCommandResult:
        context = self._require_context(actor_context)
        try:
            self.service.test_connection(
                actor_context=context,
                data_source_id=data_source_id,
            )
            return DataSourceCommandResult(
                self.query_service.get_view_for_actor(data_source_id, context)
            )
        except Exception as exc:
            self._raise_command_error(exc, context)

    def request_activation(
        self, *, data_source_id: str, actor_context: ActorContext | None
    ) -> DataSourceCommandResult:
        context = self._require_context(actor_context)
        try:
            activation_request = self.service.request_activation(
                actor_context=context,
                data_source_id=data_source_id,
            )
            return DataSourceCommandResult(
                self.query_service.get_view_for_actor(data_source_id, context),
                activation_request=activation_request,
            )
        except Exception as exc:
            self._raise_command_error(exc, context)

    def decide_activation(
        self,
        *,
        activation_request_id: str,
        decision: str,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult:
        context = self._require_context(actor_context)
        try:
            before = self.service.repository.get_activation_request(activation_request_id)
            replayed = before.status is not DataSourceActivationStatus.PENDING
            activation_request = self.service.decide_activation(
                actor_context=context,
                activation_request_id=activation_request_id,
                decision=decision,
                reason_code=reason_code,
            )
            return DataSourceCommandResult(
                self.query_service.get_view_for_actor(activation_request.data_source_id, context),
                activation_request=activation_request,
                replayed=replayed,
            )
        except AuthorizationError as exc:
            if exc.code == "DATA_SOURCE_MAKER_CHECKER_VIOLATION":
                self._audit_maker_checker_denial(context, activation_request_id)
            self._raise_command_error(exc, context)
        except Exception as exc:
            self._raise_command_error(exc, context)

    def passivate(
        self,
        *,
        data_source_id: str,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult:
        context = self._require_context(actor_context)
        try:
            self.service.deactivate_data_source(
                actor_context=context,
                data_source_id=data_source_id,
                reason_code=reason_code,
            )
            return DataSourceCommandResult(
                self.query_service.get_view_for_actor(data_source_id, context)
            )
        except Exception as exc:
            self._raise_command_error(exc, context)

    def _audit_maker_checker_denial(
        self, context: ActorContext, activation_request_id: str
    ) -> None:
        try:
            self.security_audit.append(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    session_id=context.session_id,
                    correlation_id=context.correlation_id,
                    action="DATA_SOURCE_ACTIVATION_DECISION_DENIED",
                    object_type="DataSourceActivationRequest",
                    object_id=activation_request_id,
                    result=AuditResult.DENIED,
                    reason_code="MAKER_CHECKER_VIOLATION",
                    old_values={},
                    new_values={},
                    occurred_at=datetime.now(timezone.utc),
                )
            )
        except Exception as exc:
            raise DataSourceCommandError(
                "DATA_SOURCE_AUDIT_UNAVAILABLE",
                context.correlation_id,
                category="technical",
            ) from exc

    @staticmethod
    def _require_context(context: ActorContext | None) -> ActorContext:
        if context is None:
            raise DataSourceCommandError(
                "DATA_SOURCE_PERMISSION_DENIED",
                "authorization-denied",
                category="authorization",
            )
        return context

    @staticmethod
    def _raise_command_error(exc: Exception, context: ActorContext) -> NoReturn:
        if isinstance(exc, DataSourceQueryAuthorizationError):
            raise DataSourceCommandError(
                "DATA_SOURCE_PERMISSION_DENIED",
                context.correlation_id,
                category="authorization",
            ) from exc
        if isinstance(exc, DataSourceNotFoundError):
            raise DataSourceCommandError(
                "DATA_SOURCE_NOT_FOUND",
                context.correlation_id,
                category="not_found",
            ) from exc
        if isinstance(exc, AuthorizationError):
            category = "authorization"
        elif isinstance(exc, NotFoundError):
            category = "not_found"
        elif isinstance(exc, ConflictError):
            category = "conflict"
        elif isinstance(exc, ValidationError):
            category = "validation"
        elif isinstance(exc, (TechnicalError, SecretResolutionError, AuditWriteError)):
            category = "technical"
        elif isinstance(exc, (SQLAlchemyError, DataSourceQueryTechnicalError)):
            raise DataSourceCommandError(
                "DATA_SOURCE_PERSISTENCE_UNAVAILABLE",
                context.correlation_id,
                category="technical",
            ) from exc
        else:
            raise exc
        raise DataSourceCommandError(
            getattr(exc, "code", "DATA_SOURCE_SERVICE_UNAVAILABLE"),
            context.correlation_id,
            category=category,
        ) from exc
